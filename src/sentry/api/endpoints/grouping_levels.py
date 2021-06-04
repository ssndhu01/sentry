from dataclasses import dataclass
from typing import Sequence

from rest_framework.exceptions import APIException
from snuba_sdk.query import Column, Entity, Function, Query

from sentry import features
from sentry.api.bases import GroupEndpoint
from sentry.api.endpoints.group_hashes_split import _get_group_filters
from sentry.models import Group, GroupHash
from sentry.utils import snuba


class NoEvents(APIException):
    status_code = 403
    default_detail = "This issue has no events."
    default_code = "no_events"


class MergedIssues(APIException):
    status_code = 403
    default_detail = "The issue can only contain one fingerprint. It needs to be fully unmerged before grouping levels can be shown."
    default_code = "merged_issues"


class MissingFeature(APIException):
    status_code = 403
    default_detail = "This project does not have the grouping tree feature."
    default_code = "missing_feature"


class NotHierarchical(APIException):
    status_code = 403
    default_detail = "This issue does not have hierarchical grouping."
    default_code = "not_hierarchical"


class GroupingLevelsEndpoint(GroupEndpoint):
    def get(self, request, group: Group):
        """
        Return the available levels for this group.

        ```
        GET /api/0/issues/123/grouping/levels/

        {"levels": [{"id": "0", "isCurrent": true}, {"id": "1"}, {"id": "2"}]}
        ```

        `isCurrent` is the currently applied level that the server groups by.
        It cannot be reapplied.

        The levels are returned in-order, such that the first level produces
        the least amount of issues, and the last level the most amount.

        The IDs correspond to array indices in the underlying ClickHouse column
        and are parseable as integers, but this must be treated as
        implementation detail. Clients should pass IDs around as opaque
        strings.

        A single `id` can be passed as part of the URL to
        `GroupingLevelNewIssuesEndpoint`.

        Returns a 403 if grouping levels are unavailable or the required
        featureflags are missing.
        """

        check_feature(group.project.organization, request)
        return self.respond(_list_levels(group), status=200)


def check_feature(organization, request):
    if not features.has("organizations:grouping-tree-ui", organization, actor=request.user):
        raise MissingFeature()


@dataclass
class LevelsOverview:
    current_level: int
    current_hash: str
    parent_hashes: Sequence[str]
    only_primary_hash: str
    num_levels: int


def get_levels_overview(group):
    query = (
        Query("events", Entity("events"))
        .set_select(
            [
                Column("primary_hash"),
                Function(
                    "argMax",
                    [
                        Column("hierarchical_hashes"),
                        Function("length", [Column("hierarchical_hashes")]),
                    ],
                    "longest_hierarchical_hashes",
                ),
            ]
        )
        .set_where(_get_group_filters(group))
        .set_groupby([Column("primary_hash")])
    )

    res = snuba.raw_snql_query(query, referrer="api.group_hashes_levels.get_levels_overview")

    if not res["data"]:
        raise NoEvents()

    if len(res["data"]) > 1:
        raise MergedIssues()

    assert len(res["data"]) == 1

    fields = res["data"][0]

    if not fields["longest_hierarchical_hashes"]:
        raise NotHierarchical()

    materialized_hashes = {
        hash
        for hash, in GroupHash.objects.filter(project=group.project, group=group).values_list(
            "hash"
        )
    }

    current_level = max(
        i
        for i, hash in enumerate(fields["longest_hierarchical_hashes"])
        if hash in materialized_hashes
    )

    current_hash = fields["longest_hierarchical_hashes"][current_level]
    parent_hashes = fields["longest_hierarchical_hashes"][:current_level]

    # TODO: Cache this if it takes too long. This is called from multiple
    # places, grouping overview and then again in the new-issues endpoint.

    return LevelsOverview(
        current_level=current_level,
        current_hash=current_hash,
        parent_hashes=parent_hashes,
        only_primary_hash=fields["primary_hash"],
        num_levels=len(fields["longest_hierarchical_hashes"]),
    )


def _list_levels(group):
    try:
        fields = get_levels_overview(group)
    except NoEvents:
        return {"levels": []}

    # It is a little silly to transfer a list of integers rather than just
    # giving the UI a range, but in the future we may want to add
    # additional fields to each level. Also it is good if the UI does not
    # assume too much about the form of IDs.
    levels = [{"id": str(i)} for i in range(fields.num_levels)]

    current_level = fields.current_level
    assert levels[current_level]["id"] == str(current_level)
    levels[current_level]["isCurrent"] = True
    return {"levels": levels}
