from unittest import TestCase

from sentry.models import Group, NotificationSetting, Project, User
from sentry.notifications.helpers import (
    transform_to_notification_settings_by_scope,
    transform_to_notification_settings_by_user,
)
from sentry.notifications.types import (
    NotificationScopeType,
    NotificationSettingOptionValues,
    NotificationSettingTypes,
)
from sentry.types.integrations import ExternalProviders


class TransformTestCase(TestCase):
    def setUp(self) -> None:
        self.user = User(id=1)
        self.project = Project(id=123)
        self.group = Group(id=456, project=self.project)
        self.notification_settings = [
            NotificationSetting(
                provider=ExternalProviders.SLACK.value,
                type=NotificationSettingTypes.WORKFLOW.value,
                value=NotificationSettingOptionValues.ALWAYS.value,
                target=self.user.actor,
                scope_type=NotificationScopeType.PROJECT.value,
                scope_identifier=self.project.id,
            ),
            NotificationSetting(
                provider=ExternalProviders.SLACK.value,
                type=NotificationSettingTypes.WORKFLOW.value,
                value=NotificationSettingOptionValues.ALWAYS.value,
                target=self.user.actor,
                scope_type=NotificationScopeType.USER.value,
                scope_identifier=self.user.id,
            ),
        ]


class TransformToNotificationSettingsByUserTestCase(TransformTestCase):
    def test_transform_to_notification_settings_by_user_empty(self):
        assert transform_to_notification_settings_by_user(notification_settings=[], users=[]) == {}

        assert (
            transform_to_notification_settings_by_user(notification_settings=[], users=[self.user])
            == {}
        )

    def test_transform_to_notification_settings_by_user(self):
        assert transform_to_notification_settings_by_user(
            notification_settings=self.notification_settings, users=[self.user]
        ) == {
            self.user: {
                NotificationScopeType.USER: {
                    ExternalProviders.SLACK: NotificationSettingOptionValues.ALWAYS
                },
                NotificationScopeType.PROJECT: {
                    ExternalProviders.SLACK: NotificationSettingOptionValues.ALWAYS
                },
            }
        }


class TransformToNotificationSettingsByScopeTestCase(TransformTestCase):
    def test_transform_to_notification_settings_by_scope_empty(self):
        assert transform_to_notification_settings_by_scope(notification_settings=[]) == {}

    def test_transform_to_notification_settings_by_scope(self):
        assert transform_to_notification_settings_by_scope(
            notification_settings=self.notification_settings,
        ) == {
            NotificationScopeType.USER: {
                self.user.id: {ExternalProviders.SLACK: NotificationSettingOptionValues.ALWAYS},
            },
            NotificationScopeType.PROJECT: {
                self.project.id: {
                    ExternalProviders.SLACK: NotificationSettingOptionValues.ALWAYS,
                }
            },
        }
