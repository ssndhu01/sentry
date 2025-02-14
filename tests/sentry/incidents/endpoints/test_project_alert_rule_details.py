from exam import fixture

from sentry.api.serializers import serialize
from sentry.incidents.models import (
    AlertRule,
    AlertRuleStatus,
    AlertRuleTrigger,
    AlertRuleTriggerAction,
    Incident,
    IncidentStatus,
)
from sentry.models import Integration
from sentry.testutils import APITestCase
from sentry.utils.compat.mock import patch


class AlertRuleDetailsBase:
    endpoint = "sentry-api-0-project-alert-rule-details"

    @fixture
    def valid_params(self):
        return {
            "name": "hello",
            "time_window": 10,
            "query": "level:error",
            "threshold_type": 0,
            "resolve_threshold": 100,
            "alert_threshold": 0,
            "aggregate": "count_unique(user)",
            "threshold_period": 1,
            "projects": [self.project.slug],
            "triggers": [
                {
                    "label": "critical",
                    "alertThreshold": 200,
                    "actions": [
                        {"type": "email", "targetType": "team", "targetIdentifier": self.team.id}
                    ],
                },
                {
                    "label": "warning",
                    "alertThreshold": 150,
                    "actions": [
                        {"type": "email", "targetType": "team", "targetIdentifier": self.team.id},
                        {"type": "email", "targetType": "user", "targetIdentifier": self.user.id},
                    ],
                },
            ],
        }

    def get_serialized_alert_rule(self):
        # Only call after calling self.alert_rule to create it.
        original_endpoint = self.endpoint
        original_method = self.method
        self.endpoint = "sentry-api-0-organization-alert-rules"
        self.method = "get"
        with self.feature("organizations:incidents"):
            resp = self.get_valid_response(self.organization.slug)
            assert len(resp.data) >= 1
            serialized_alert_rule = resp.data[0]
        self.endpoint = original_endpoint
        self.method = original_method
        return serialized_alert_rule

    @fixture
    def organization(self):
        return self.create_organization()

    @fixture
    def project(self):
        return self.create_project(organization=self.organization)

    @fixture
    def user(self):
        return self.create_user()

    @fixture
    def alert_rule(self):
        return self.create_alert_rule(name="hello")

    def test_invalid_rule_id(self):
        self.create_member(
            user=self.user, organization=self.organization, role="owner", teams=[self.team]
        )
        self.login_as(self.user)
        with self.feature("organizations:incidents"):
            resp = self.get_response(self.organization.slug, self.project.slug, 1234)

        assert resp.status_code == 404

    def test_permissions(self):
        self.create_team(organization=self.organization, members=[self.user])
        self.login_as(self.create_user())
        with self.feature("organizations:incidents"):
            resp = self.get_response(self.organization.slug, self.project.slug, self.alert_rule.id)

        assert resp.status_code == 403

    def test_no_feature(self):
        self.create_member(
            user=self.user, organization=self.organization, role="owner", teams=[self.team]
        )
        self.login_as(self.user)
        resp = self.get_response(self.organization.slug, self.project.slug, self.alert_rule.id)
        assert resp.status_code == 404


class AlertRuleDetailsGetEndpointTest(AlertRuleDetailsBase, APITestCase):
    def test_simple(self):
        self.create_team(organization=self.organization, members=[self.user])
        self.login_as(self.user)
        with self.feature("organizations:incidents"):
            resp = self.get_valid_response(
                self.organization.slug, self.project.slug, self.alert_rule.id
            )

        assert resp.data == serialize(self.alert_rule)

    def test_aggregate_translation(self):
        self.create_member(
            user=self.user, organization=self.organization, role="owner", teams=[self.team]
        )
        self.login_as(self.user)
        alert_rule = self.create_alert_rule(aggregate="count_unique(tags[sentry:user])")
        with self.feature("organizations:incidents"):
            resp = self.get_valid_response(self.organization.slug, self.project.slug, alert_rule.id)
            assert resp.data["aggregate"] == "count_unique(user)"
            assert alert_rule.snuba_query.aggregate == "count_unique(tags[sentry:user])"


class AlertRuleDetailsPutEndpointTest(AlertRuleDetailsBase, APITestCase):
    method = "put"

    def test_simple(self):
        self.create_member(
            user=self.user, organization=self.organization, role="owner", teams=[self.team]
        )

        test_params = self.valid_params.copy()
        test_params["resolve_threshold"] = self.alert_rule.resolve_threshold
        test_params.update({"name": "what"})

        self.login_as(self.user)
        with self.feature("organizations:incidents"):
            resp = self.get_valid_response(
                self.organization.slug, self.project.slug, self.alert_rule.id, **test_params
            )

        self.alert_rule.refresh_from_db()
        self.alert_rule.name = "what"
        self.alert_rule.snuba_query.refresh_from_db()
        assert resp.data == serialize(self.alert_rule)
        assert resp.data["name"] == "what"

    def test_not_updated_fields(self):
        test_params = self.valid_params.copy()
        test_params["resolve_threshold"] = self.alert_rule.resolve_threshold
        test_params["aggregate"] = self.alert_rule.snuba_query.aggregate

        self.create_member(
            user=self.user, organization=self.organization, role="owner", teams=[self.team]
        )

        self.login_as(self.user)
        with self.feature("organizations:incidents"):
            resp = self.get_valid_response(
                self.organization.slug, self.project.slug, self.alert_rule.id, **test_params
            )

        existing_sub = self.alert_rule.snuba_query.subscriptions.first()

        # Alert rule should be exactly the same
        self.alert_rule.refresh_from_db()
        assert resp.data == serialize(self.alert_rule)
        # If the aggregate changed we'd have a new subscription, validate that
        # it hasn't changed explicitly
        updated_sub = AlertRule.objects.get(id=self.alert_rule.id).snuba_query.subscriptions.first()
        assert updated_sub.subscription_id == existing_sub.subscription_id

    def test_update_snapshot(self):
        self.create_member(
            user=self.user, organization=self.organization, role="owner", teams=[self.team]
        )
        self.login_as(self.user)
        alert_rule = self.alert_rule
        # We need the IDs to force update instead of create, so we just get the rule using our own API. Like frontend would.
        serialized_alert_rule = self.get_serialized_alert_rule()

        # Archive the rule so that the endpoint 404s:
        alert_rule.status = AlertRuleStatus.SNAPSHOT.value
        alert_rule.save()

        with self.feature("organizations:incidents"):
            self.get_valid_response(
                self.organization.slug,
                self.project.slug,
                alert_rule.id,
                status_code=404,
                **serialized_alert_rule,
            )

    @patch(
        "sentry.integrations.slack.utils.get_channel_id_with_timeout",
        return_value=("#", None, True),
    )
    @patch("sentry.integrations.slack.tasks.find_channel_id_for_alert_rule.apply_async")
    @patch("sentry.integrations.slack.tasks.uuid4")
    def test_kicks_off_slack_async_job(
        self, mock_uuid4, mock_find_channel_id_for_alert_rule, mock_get_channel_id
    ):
        mock_uuid4.return_value = self.get_mock_uuid()
        self.create_member(
            user=self.user, organization=self.organization, role="owner", teams=[self.team]
        )
        self.login_as(self.user)
        self.integration = Integration.objects.create(
            provider="slack",
            name="Team A",
            external_id="TXXXXXXX1",
            metadata={"access_token": "xoxp-xxxxxxxxx-xxxxxxxxxx-xxxxxxxxxxxx"},
        )
        self.integration.add_organization(self.organization, self.user)
        test_params = self.valid_params.copy()
        test_params["triggers"] = [
            {
                "label": "critical",
                "alertThreshold": 200,
                "actions": [
                    {
                        "type": "slack",
                        "targetIdentifier": "my-channel",
                        "targetType": "specific",
                        "integration": self.integration.id,
                    }
                ],
            },
        ]

        with self.feature("organizations:incidents"):
            resp = self.get_response(
                self.organization.slug, self.project.slug, self.alert_rule.id, **test_params
            )

        # resp.data["uuid"] = "abc123" # TODO: @scefali: Does this do anything? I think it can be removed
        assert resp.data["uuid"] == "abc123"  # TODO: @scefali: You probably meant to do this?
        kwargs = {
            "organization_id": self.organization.id,
            "uuid": "abc123",
            "alert_rule_id": self.alert_rule.id,
            "data": test_params,
            "user_id": self.user.id,
        }
        mock_find_channel_id_for_alert_rule.assert_called_once_with(kwargs=kwargs)

    @patch(
        "sentry.integrations.slack.utils.get_channel_id_with_timeout",
        side_effect=[("#", 10, False), ("#", 10, False), ("#", 20, False)],
    )
    @patch("sentry.integrations.slack.tasks.uuid4")
    def test_async_lookup_outside_transaction(self, mock_uuid4, mock_get_channel_id):
        mock_uuid4.return_value = self.get_mock_uuid()

        from sentry.integrations.slack.utils import get_channel_id_with_timeout

        with patch(
            "sentry.integrations.slack.utils.get_channel_id_with_timeout",
            wraps=get_channel_id_with_timeout,
        ) as mock_get_channel_id:
            self.create_member(
                user=self.user, organization=self.organization, role="owner", teams=[self.team]
            )
            self.login_as(self.user)
            self.integration = Integration.objects.create(
                provider="slack",
                name="Team A",
                external_id="TXXXXXXX1",
                metadata={"access_token": "xoxp-xxxxxxxxx-xxxxxxxxxx-xxxxxxxxxxxx"},
            )
            self.integration.add_organization(self.organization, self.user)
            test_params = self.valid_params.copy()
            test_params["triggers"] = [
                {
                    "label": "critical",
                    "alertThreshold": 200,
                    "actions": [
                        {
                            "type": "slack",
                            "targetIdentifier": "my-channel",
                            "targetType": "specific",
                            "integration": self.integration.id,
                        },
                    ],
                },
            ]

            with self.feature("organizations:incidents"), self.tasks():
                resp = self.get_response(
                    self.organization.slug, self.project.slug, self.alert_rule.id, **test_params
                )
            assert resp.data["uuid"] == "abc123"
            assert mock_get_channel_id.call_count == 1
            # Using get deliberately as there should only be one. Test should fail otherwise.
            trigger = AlertRuleTrigger.objects.get(alert_rule_id=self.alert_rule.id)
            action = AlertRuleTriggerAction.objects.get(alert_rule_trigger=trigger)
            assert action.target_identifier == "10"
            assert action.target_display == "my-channel"

            # Now two actions with slack:
            test_params = self.valid_params.copy()
            test_params["triggers"] = [
                {
                    "label": "critical",
                    "alertThreshold": 200,
                    "actions": [
                        {
                            "type": "slack",
                            "targetIdentifier": "my-channel",
                            "targetType": "specific",
                            "integration": self.integration.id,
                        },
                        {
                            "type": "slack",
                            "targetIdentifier": "another-channel",
                            "targetType": "specific",
                            "integration": self.integration.id,
                        },
                        {
                            "type": "slack",
                            "targetIdentifier": "another-channel",
                            "targetType": "specific",
                            "integration": self.integration.id,
                        },
                    ],
                },
                {
                    "label": "warning",
                    "alertThreshold": 200,
                    "actions": [
                        {
                            "type": "slack",
                            "targetIdentifier": "my-channel",  # same channel, but only one lookup made per channel
                            "targetType": "specific",
                            "integration": self.integration.id,
                        },
                    ],
                },
            ]

            with self.feature("organizations:incidents"), self.tasks():
                resp = self.get_response(
                    self.organization.slug, self.project.slug, self.alert_rule.id, **test_params
                )
            assert resp.data["uuid"] == "abc123"
            assert (
                mock_get_channel_id.call_count == 3
            )  # just made 2 calls, plus the call from the single action test

            # Using get deliberately as there should only be one. Test should fail otherwise.
            triggers = AlertRuleTrigger.objects.filter(alert_rule_id=self.alert_rule.id)
            actions = AlertRuleTriggerAction.objects.filter(
                alert_rule_trigger__in=triggers
            ).order_by("id")
            # The 3 critical trigger actions:
            assert actions[0].target_identifier == "10"
            assert actions[0].target_display == "my-channel"
            assert actions[1].target_identifier == "20"
            assert actions[1].target_display == "another-channel"
            assert actions[2].target_identifier == "20"
            assert actions[2].target_display == "another-channel"

            # This is the warning trigger action:
            assert actions[3].target_identifier == "10"
            assert actions[3].target_display == "my-channel"

            # Now an invalid action (we want to early out with a good validationerror and not schedule the task):
            name = "MyInvalidActionRule"
            test_params["name"] = name
            test_params["triggers"] = [
                {
                    "label": "critical",
                    "alertThreshold": 75,
                    "actions": [
                        {
                            "type": "element",
                            "targetIdentifier": "my-channel",
                            "targetType": "arbitrary",
                            "integrationId": self.integration.id,
                        },
                    ],
                },
            ]
            with self.feature("organizations:incidents"), self.tasks():
                resp = self.get_response(
                    self.organization.slug, self.project.slug, self.alert_rule.id, **test_params
                )
            assert resp.status_code == 400
            assert (
                mock_get_channel_id.call_count == 3
            )  # Did not increment from the last assertion because we early out on the validation error

    def test_no_owner(self):
        self.create_member(
            user=self.user, organization=self.organization, role="owner", teams=[self.team]
        )

        self.login_as(self.user)

        alert_rule = self.alert_rule
        alert_rule.owner = self.user.actor
        alert_rule.save()
        assert alert_rule.owner == self.user.actor

        test_params = self.valid_params.copy()
        test_params["resolve_threshold"] = self.alert_rule.resolve_threshold
        test_params["owner"] = None

        with self.feature("organizations:incidents"):
            resp = self.get_valid_response(
                self.organization.slug, self.project.slug, alert_rule.id, **test_params
            )

        alert_rule.refresh_from_db()
        alert_rule.snuba_query.refresh_from_db()
        assert resp.data == serialize(alert_rule, self.user)
        assert (
            resp.data["owner"] == self.user.actor.get_actor_identifier()
        )  # Doesn't unassign yet - TDB in future though


class AlertRuleDetailsDeleteEndpointTest(AlertRuleDetailsBase, APITestCase):
    method = "delete"

    def test_simple(self):
        self.create_member(
            user=self.user, organization=self.organization, role="owner", teams=[self.team]
        )
        self.login_as(self.user)
        with self.feature("organizations:incidents"):
            self.get_valid_response(
                self.organization.slug, self.project.slug, self.alert_rule.id, status_code=204
            )

        assert not AlertRule.objects.filter(id=self.alert_rule.id).exists()
        assert not AlertRule.objects_with_snapshots.filter(name=self.alert_rule.id).exists()
        assert not AlertRule.objects_with_snapshots.filter(id=self.alert_rule.id).exists()

    def test_snapshot_and_create_new_with_same_name(self):
        with self.tasks():
            self.create_member(
                user=self.user, organization=self.organization, role="owner", teams=[self.team]
            )
            self.login_as(self.user)

            # We attach the rule to an incident so the rule is snapshotted instead of deleted.
            incident = self.create_incident(alert_rule=self.alert_rule)

            with self.feature("organizations:incidents"):
                self.get_valid_response(
                    self.organization.slug, self.project.slug, self.alert_rule.id, status_code=204
                )

            alert_rule = AlertRule.objects_with_snapshots.get(id=self.alert_rule.id)

            assert not AlertRule.objects.filter(id=alert_rule.id).exists()
            assert AlertRule.objects_with_snapshots.filter(id=alert_rule.id).exists()
            assert alert_rule.status == AlertRuleStatus.SNAPSHOT.value

            # We also confirm that the incident is automatically resolved.
            assert Incident.objects.get(id=incident.id).status == IncidentStatus.CLOSED.value
