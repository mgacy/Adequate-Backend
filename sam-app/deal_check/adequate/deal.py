from datetime import datetime as dt
from datetime import time
from .models import DealDelta, LaunchStatus
from .tz_support import Eastern

CURRENT_ID_KEY_VALUE = 'current_deal'

# Meh Launch Schedule
PREMIER_HOUR = 0
RELAUNCH_HOUR = 8
RESERVE_HOUR = 16

# TODO: look into using `difflib` library?


# ----------------------------------------------------------------------------
# Primary Functions

# FIXME: it is confusing that (a) this is named `delta` and (b) we have a `DealDelta` type, yet this returns a dict  # noqa E501
def delta(current, update, now=None):
    """Return changes between `current` and `update` to use as mutation input.

    Parameters
    ----------
    current : dict
        Deal fetched from Adequate API
    update : dict
        Deal fetched from meh.com API
    now : datetime, optional
        Current datetime

    Returns
    -------
    dict
        Input for `AppSync.update_deal()`

        _version : int
            Deal `_version`
        id : str
            Deal `id`
        launches : list[dict], optional
            Deal `launches`
        launchStatus : str, optional
            Deal `launchStatus`
        soldOutAt : str, optional
            Deal `soldOutAt`
        topic : dict, optional
            Deal `topic`
    """
    delta = _diff_launches(current, update)

    launch_status = _diff_launch_status(current, delta, now)
    if launch_status:
        delta['launchStatus'] = launch_status.name

    topic = _diff_topic(current, update)
    if topic:
        delta['topic'] = topic

    # UpdateDealInput.id is non-nullable
    if delta:
        delta['id'] = CURRENT_ID_KEY_VALUE
        delta['_version'] = current.get('_version', 1)

    return delta


# TODO: fix overlap between this and `_diff_launch_status()`
def get_launch_status(deal, now=None):
    """Return `LaunchStatus` for `deal`.

    Parameters
    ----------
    deal : dict
        Description
    now : datetime, optional
        Current datetime

    Returns
    -------
    LaunchStatus
        Description

    Raises
    ------
    ValueError
        Description
    """
    if deal.get('soldOutAt', None):
        return LaunchStatus.soldOut

    # Provide option to pass `now` for testing
    if now is None:
        now = dt.now(tz=Eastern).timetz()
    relaunch = time(hour=RELAUNCH_HOUR, tzinfo=Eastern)
    reserve = time(hour=RESERVE_HOUR, tzinfo=Eastern)

    launches = deal.get('launches', [])
    if launches:
        if len(launches) != 2:
            raise ValueError(
                f"Malformed `launches` - Received {launches}. "
                "Expected 2 k, v pairs."
            )

        if launches[1].get('soldOutAt'):
            if now < reserve:
                return LaunchStatus.relaunchSoldOut
            else:
                return LaunchStatus.reserve

        # Relaunch
        elif launches[0].get('soldOutAt'):
            # TODO: do we need more checks here?
            if now < relaunch:
                return LaunchStatus.launchSoldOut
            else:
                return LaunchStatus.relaunch

    # No sell out events
    if now >= relaunch:
        return LaunchStatus.relaunch
    else:
        return LaunchStatus.launch


# ----------------------------------------------------------------------------
# Internal Functions

def _diff_launches(current, update):
    """Docstring.

    Parameters
    ----------
    current : dict
        Deal fetched from Adequate API
    update : dict
        Deal fetched from meh.com API

    Returns
    -------
    dict
        Description

        soldOutAt : str, optional
            Deal `soldOutAt`
        launches : list[dict], optional
            Deal `launches`
    """
    delta = {}

    sold_out_at = update.get('soldOutAt', None)
    if sold_out_at and sold_out_at != current.get('soldOutAt', None):
        delta.update({'soldOutAt': sold_out_at})

    launches = update.get('launches', [])
    if launches and (launches != current.get('launches', [])):
        delta.update({'launches': launches})

    return delta


def _diff_launch_status(current, delta, now=None):
    """Summary

    Parameters
    ----------
    current : dict
        Deal fetched from Adequate API
    delta : dict
        Description
    now : datetime, optional
        Current datetime

    Returns
    -------
    TYPE
        Description

    Raises
    ------
    ValueError
        Description
    """
    # TODO: pass `delta` or just `delta['launches']`?

    # Provide option to pass `now` for testing
    if now is None:
        now = dt.now(tz=Eastern).timetz()
    relaunch = time(hour=RELAUNCH_HOUR, tzinfo=Eastern)
    reserve = time(hour=RESERVE_HOUR, tzinfo=Eastern)

    status = None

    cs = current.get('launchStatus', None)
    try:
        cs = LaunchStatus[cs]
    except (TypeError, KeyError):
        statuses = [k for k, _ in LaunchStatus.__members__.items()]
        raise ValueError(
            f"Invalid LaunchStatus - Received {cs}. "
            f"Valid LaunchStatus values are {statuses}"
        )

    dl = delta.get('launches', [])

    if delta.get('soldOutAt', None):
        status = LaunchStatus.soldOut

    # Changes to `launches`
    elif dl:
        if len(dl) != 2:
            raise ValueError(
                f"Malformed `launches` - Received {dl}. Expected 2 k, v pairs."
            )

        # Reserve
        if dl[1].get('soldOutAt'):
            if now < reserve:
                status = LaunchStatus.relaunchSoldOut
            else:
                status = LaunchStatus.reserve

        # Relaunch
        elif dl[0].get('soldOutAt'):
            # TODO: do we need more checks here?
            if now < relaunch:
                status = LaunchStatus.launchSoldOut
            else:
                status = LaunchStatus.relaunch

        else:
            # TODO: should we just raise an exception here?

            # A delta with a `launches` value of
            # `[{'soldOutAt': None}, {'soldOutAt': None}]` would imply that:
            # (1) `current` lacked a valid  `launches` value
            # (2) one of the launches is no longer sold out
            # (3) the value of one of the `soldOutAt` changed
            # None of these should be valid states

            if now >= reserve:
                status = LaunchStatus.reserve
            elif now >= relaunch:
                status = LaunchStatus.relaunch
            else:
                status = LaunchStatus.launch

    # No changes to `launches`
    else:
        # TODO: do we need to do any additional verification?
        if (
            cs == LaunchStatus.relaunchSoldOut
            and now >= reserve
        ):
            status = LaunchStatus.reserve
        elif (
            (cs == LaunchStatus.launch or cs == LaunchStatus.launchSoldOut)
            and now >= relaunch
        ):
            status = LaunchStatus.relaunch

    # TODO: is it really possible for the following to not be true?
    if status and status != cs:
        return status
    else:
        return None
    # return status


def _diff_topic(current, update):
    """Summary.

    Data:

    {
        'commentCount': int,
        'createdAt': string,
        'id': string,
        'replyCount': int,
        'url': string,
        'voteCount': int
    }

    Parameters
    ----------
    current : dict
        Description
    update : dict
        Deal fetched from meh.com API

    Returns
    -------
    dict
        Description
    """

    # Check for changes to `topic` ...
    # TODO: should we pass the entire `deal` or just `deal.topic`?
    curr_topic = current.get('topic', {})
    updt_topic = update.get('topic', {})

    # All fields of the `TopicInput` for `UpdateDealInput` are non-nullable
    # TODO: would we ever have an issue with the update having missing fields?
    if updt_topic != curr_topic:
        return updt_topic
    else:
        return {}

    """
    delta = {}

    new_comment = updt_topic.get('commentCount', None)
    if new_comment and new_comment != curr_topic.get('commentCount', None):
        delta['commentCount'] = new_comment

    new_reply = updt_topic.get('replyCount', None)
    if new_reply and new_reply != curr_topic.get('replyCount', None):
        delta['replyCount'] = new_reply

    new_vote = updt_topic.get('voteCount', None)
    if new_vote and new_vote != curr_topic.get('voteCount', None):
        delta['voteCount'] = new_vote

    # If the following apply, they should all be additions, not changes
    new_id = updt_topic.get('id', None)
    if new_id and new_id != curr_topic.get('id', None):
        delta['id'] = new_id

    new_url = updt_topic.get('url', None)
    if new_url and new_url != curr_topic.get('url', None):
        delta['url'] = new_url

    new_created = updt_topic.get('createdAt', None)
    if new_created and new_created != curr_topic.get('createdAt', None):
        delta['createdAt'] = new_created

    if delta:
        delta['id'] = curr_topic['id']
    """
    return delta


# TODO: am I still using this and what is its relation to `delta_message()`?
def _diff_deal_delta(delta):
    """Returns dict of DealDelta keys and corresponding values for a mutation
    input.

    Parameters
    ----------
    delta : dict
        Variables for GraphQL mutation input

    Returns
    -------
    dict
        DealDelta keys and corresponding values

    Raises
    ------
    ValueError
        Description
    """
    deal_delta = {}

    # TODO: should I really bother with conversion to Enums?
    launch_status = delta.get('launchStatus', None)
    if launch_status:
        # TODO: should we really need error handling here?
        try:
            status = LaunchStatus[launch_status]
        except (TypeError, KeyError):
            statuses = [k for k, _ in LaunchStatus.__members__.items()]
            raise ValueError(
                f"Invalid LaunchStatus - Received {launch_status}. Valid LaunchStatus values are {statuses}"  # noqa E501
            )
        deal_delta[DealDelta.launchStatus] = status

    comment_count = delta.get('topic', {}).get('commentCount', None)
    if comment_count:
        deal_delta[DealDelta.commentCount] = comment_count

    return deal_delta
