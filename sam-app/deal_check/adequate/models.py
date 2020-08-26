from enum import Enum


# @enum.unique
class DealDelta(Enum):
    newDeal = 'newDeal'
    commentCount = 'commentCount'
    launchStatus = 'launchStatus'
    # multiple = multiple


# @enum.unique
class LaunchStatus(Enum):
    launch = 'launch'
    launchSoldOut = 'launchSoldOut'
    relaunch = 'relaunch'
    relaunchSoldOut = 'relaunchSoldOut'
    reserve = 'reserve'
    soldOut = 'soldOut'
    expired = 'expired'
