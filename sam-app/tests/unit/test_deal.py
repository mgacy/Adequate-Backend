import copy
from datetime import time
import json
from pathlib import Path
import unittest
from deal_check.adequate.deal import PREMIER_HOUR, RELAUNCH_HOUR, RESERVE_HOUR
from deal_check.adequate.deal import DealDelta, LaunchStatus
from deal_check.adequate.deal import _diff_launches, _diff_launch_status, _diff_topic, _diff_deal_delta  # noqa E501
from deal_check.adequate.tz_support import Eastern


class DealTestCase(unittest.TestCase):

    base_path = Path(__file__).parent
    def_deal = 'meh_response_1.json'

    # date_format = '%Y-%m-%dT%H:%M:%S'  # + now.strftime('.%f')[:4] + 'Z'
    soldOutAt_1 = '2020-06-15T05:49:42.023Z'
    soldOutAt_2 = '2020-06-15T19:49:42.023Z'
    soldOutAt_3 = '2020-06-15T19:49:42.023Z'

    # Should we load the deal in `setUp`?

    # def setUp(self):
    #     self.current = self.load_deal(self.def_deal)

    # def tearDown(self):

    # A

    def load_deal(self, file):
        path = (self.base_path / 'data' / file).resolve()
        with open(path, 'r') as f:
            file_contents = json.load(f)
        return file_contents

    # ------------------------------------------------------------------------
    # Launches

    """
    def test_launches_STATE_TEMPLATE(self):
        current = self.load_deal(self.def_deal)
        current['launches'] = None
        # current['launchStatus'] = None
        current.pop('soldOutAt', None)

        # Changes
        delta = {}

        update = copy.deepcopy(current)
        update.update(delta)

        expected = delta

        result = _diff_launches(current, update)
        self.assertEqual(result, expected)
    """

    def test_launches_launchSoldOut(self):
        current = self.load_deal(self.def_deal)
        current['launches'] = [
            {'soldOutAt': None},
            {'soldOutAt': None},
        ]
        # current['launchStatus'] = LaunchStatus.launch.name
        current.pop('soldOutAt', None)

        # Changes
        delta = {
            'launches': [
                {'soldOutAt': self.soldOutAt_1},
                {'soldOutAt': None},
            ]
        }
        # ds = {
        #     'launchStatus': LaunchStatus.launchSoldOut.name
        # }

        update = copy.deepcopy(current)
        update.update(delta)

        expected = delta

        # hour = PREMIER_HOUR + 4
        # minute = 1
        # now = time(hour=hour, minute=minute, tzinfo=Eastern)

        result = _diff_launches(current, update)
        self.assertEqual(result, expected)

    def test_launches_relaunchSoldOut_1(self):
        current = self.load_deal(self.def_deal)
        current['launches'] = [
            {'soldOutAt': self.soldOutAt_1},
            {'soldOutAt': None},
        ]
        current.pop('soldOutAt', None)

        # Changes
        delta = {
            'launches': [
                {'soldOutAt': self.soldOutAt_1},
                {'soldOutAt': self.soldOutAt_2},
            ]
        }

        update = copy.deepcopy(current)
        update.update(delta)

        expected = delta

        result = _diff_launches(current, update)
        self.assertEqual(result, expected)

    def test_launches_relaunchSoldOut_2(self):
        current = self.load_deal(self.def_deal)
        current['launches'] = [
            {'soldOutAt': None},
            {'soldOutAt': None},
        ]
        current.pop('soldOutAt', None)

        # Changes
        delta = {
            'launches': [
                {'soldOutAt': None},
                {'soldOutAt': self.soldOutAt_2},
            ]
        }

        update = copy.deepcopy(current)
        update.update(delta)

        expected = delta

        result = _diff_launches(current, update)
        self.assertEqual(result, expected)

    def test_launches_soldOut_1(self):
        current = self.load_deal(self.def_deal)
        current['launches'] = [
            {'soldOutAt': self.soldOutAt_1},
            {'soldOutAt': self.soldOutAt_2},
        ]
        current.pop('soldOutAt', None)

        # Changes
        delta = {
            'soldOutAt': self.soldOutAt_3
        }

        update = copy.deepcopy(current)
        update.update(delta)

        expected = delta

        result = _diff_launches(current, update)
        self.assertEqual(result, expected)

    def test_launches_soldOut_2(self):
        current = self.load_deal(self.def_deal)
        current['launches'] = [
            {'soldOutAt': None},
            {'soldOutAt': self.soldOutAt_2},
        ]
        current.pop('soldOutAt', None)

        # Changes
        delta = {
            'soldOutAt': self.soldOutAt_3
        }

        update = copy.deepcopy(current)
        update.update(delta)

        expected = delta

        result = _diff_launches(current, update)
        self.assertEqual(result, expected)

    def test_launches_soldOut_3(self):
        current = self.load_deal(self.def_deal)
        current['launches'] = [
            {'soldOutAt': None},
            {'soldOutAt': None},
        ]
        current.pop('soldOutAt', None)

        # Changes
        delta = {
            'soldOutAt': self.soldOutAt_3
        }

        update = copy.deepcopy(current)
        update.update(delta)

        expected = delta

        result = _diff_launches(current, update)
        self.assertEqual(result, expected)

    # ------------------------------------------------------------------------
    # LaunchStatus

    """
    def test_STATUS_TEMPLATE(self):
        current = self.load_deal(self.def_deal)
        current['launches'] = None
        current['launchStatus'] = None
        current.pop('soldOutAt', None)

        # Changes
        delta = {}

        # Now
        hour = RESERVE_HOUR
        minute = 0
        second = 0
        now = time(hour=hour, minute=minute, second=second, tzinfo=Eastern)

        expected = LaunchStatus
        result = _diff_launch_status(current, delta, now)
        self.assertEqual(result, expected)
    """

    # .launchSoldOut

    def test_launchStatus_launchSoldOut_1(self):
        """Premier launch sold out - 04:01.
        """
        current = self.load_deal(self.def_deal)
        current['launches'] = [
            {'soldOutAt': None},
            {'soldOutAt': None},
        ]
        current['launchStatus'] = LaunchStatus.launch.name
        current.pop('soldOutAt', None)

        # Changes
        delta = {
            'launches': [
                {'soldOutAt': self.soldOutAt_1},
                {'soldOutAt': None},
            ]
        }

        # Now
        hour = PREMIER_HOUR + 4
        minute = 1
        second = 0
        now = time(hour=hour, minute=minute, second=second, tzinfo=Eastern)

        expected = LaunchStatus.launchSoldOut
        result = _diff_launch_status(current, delta, now)
        self.assertEqual(result, expected)

    def test_launchStatus_launchSoldOut_right_before_relaunch(self):
        """Premier launch sold out right before Relaunch - 08:59:59.
        """
        current = self.load_deal(self.def_deal)
        current['launches'] = [
            {'soldOutAt': None},
            {'soldOutAt': None},
        ]
        current['launchStatus'] = LaunchStatus.launch.name
        current.pop('soldOutAt', None)

        # Changes
        delta = {
            'launches': [
                {'soldOutAt': self.soldOutAt_1},
                {'soldOutAt': None},
            ]
        }

        # Now
        hour = RELAUNCH_HOUR - 1
        minute = 59
        second = 59
        now = time(hour=hour, minute=minute, second=second, tzinfo=Eastern)

        expected = LaunchStatus.launchSoldOut
        result = _diff_launch_status(current, delta, now)
        self.assertEqual(result, expected)

    # .relaunch

    def test_launchStatus_relaunch_launch_sells_out_right_at_relaunch(self):
        """Launch sold out just before, but has now Relaunched - 09:00.
        """
        current = self.load_deal(self.def_deal)
        current['launches'] = [
            {'soldOutAt': None},
            {'soldOutAt': None},
        ]
        current['launchStatus'] = LaunchStatus.launch.name
        current.pop('soldOutAt', None)

        # Changes
        delta = {
            'launches': [
                {'soldOutAt': self.soldOutAt_1},
                {'soldOutAt': None},
            ]
        }

        # Now
        hour = RELAUNCH_HOUR
        minute = 0
        second = 0
        now = time(hour=hour, minute=minute, second=second, tzinfo=Eastern)

        expected = LaunchStatus.relaunch
        result = _diff_launch_status(current, delta, now)
        self.assertEqual(result, expected)

    def test_launchStatus_relaunch_launch_sells_out_right_at_relaunch_b(self):
        """Premier launch sold out just before Relaunch, now just after - 09:01.
        """
        current = self.load_deal(self.def_deal)
        current['launches'] = [
            {'soldOutAt': None},
            {'soldOutAt': None},
        ]
        # We are assuming the premier launch sold out since last check.
        current['launchStatus'] = LaunchStatus.launch.name
        current.pop('soldOutAt', None)

        # Changes
        delta = {
            'launches': [
                {'soldOutAt': self.soldOutAt_1},
                {'soldOutAt': None},
            ]
        }

        # Now
        hour = RELAUNCH_HOUR
        minute = 1  # <- Difference from above
        now = time(hour=hour, minute=minute, tzinfo=Eastern)

        expected = LaunchStatus.relaunch
        result = _diff_launch_status(current, delta, now)
        self.assertEqual(result, expected)

    def test_launchStatus_relaunch_without_premier_sell_out(self):
        """Premier launch did not sell out - Relaunch - 09:00.
        """
        current = self.load_deal(self.def_deal)
        current['launches'] = [
            {'soldOutAt': None},
            {'soldOutAt': None},
        ]
        current['launchStatus'] = LaunchStatus.launch.name
        current.pop('soldOutAt', None)

        # Changes
        delta = {}

        # Now
        hour = RELAUNCH_HOUR
        minute = 0
        second = 0
        now = time(hour=hour, minute=minute, second=second, tzinfo=Eastern)

        expected = LaunchStatus.relaunch
        result = _diff_launch_status(current, delta, now)
        self.assertEqual(result, expected)

    def test_launchStatus_relaunch_no_status_change(self):
        """No changes after Relaunch - 09:00:01.
        """
        current = self.load_deal(self.def_deal)
        # TODO: should Premier have sold out / does it matter / test anyways?
        current['launches'] = [
            {'soldOutAt': None},
            {'soldOutAt': None},
        ]
        current['launchStatus'] = LaunchStatus.relaunch.name
        current.pop('soldOutAt', None)

        # Changes
        delta = {}

        # Now
        hour = RELAUNCH_HOUR
        minute = 0
        second = 1
        now = time(hour=hour, minute=minute, second=second, tzinfo=Eastern)

        expected = None
        result = _diff_launch_status(current, delta, now)
        self.assertEqual(result, expected)

    def test_launchStatus_reserve_no_status_change(self):
        """No changes after Reserve - 16:00:01.
        """
        current = self.load_deal(self.def_deal)
        current['launches'] = [
            {'soldOutAt': None},
            {'soldOutAt': None},
        ]
        current['launchStatus'] = LaunchStatus.relaunch.name
        current.pop('soldOutAt', None)

        # Changes
        delta = {}

        # Now
        hour = RESERVE_HOUR
        minute = 0
        second = 1
        now = time(hour=hour, minute=minute, second=second, tzinfo=Eastern)

        expected = None 
        result = _diff_launch_status(current, delta, now)
        self.assertEqual(result, expected)

    # Launch sells out right after Relaunch
    # Launch sells out right before Relaunch

    # .relaunchSoldOut

    def test_launchStatus_relaunchSoldOut_1(self):
        current = self.load_deal(self.def_deal)
        current['launches'] = [
            {'soldOutAt': None},
            {'soldOutAt': None},
        ]
        current['launchStatus'] = LaunchStatus.relaunch.name
        current.pop('soldOutAt', None)

        # Changes
        delta = {
            'launches': [
                {'soldOutAt': None},
                {'soldOutAt': self.soldOutAt_2},
            ]
        }

        # Now
        hour = RELAUNCH_HOUR + 1
        minute = 1
        now = time(hour=hour, minute=minute, tzinfo=Eastern)

        expected = LaunchStatus.relaunchSoldOut
        result = _diff_launch_status(current, delta, now)
        self.assertEqual(result, expected)

    # Sells out right after Relaunch?

    def test_launchStatus_relaunchSoldOut_2(self):
        current = self.load_deal(self.def_deal)
        current['launches'] = [
            {'soldOutAt': self.soldOutAt_1},  # <- Difference from above
            {'soldOutAt': None},
        ]
        current['launchStatus'] = LaunchStatus.relaunch.name
        current.pop('soldOutAt', None)

        # Changes
        delta = {
            'launches': [
                {'soldOutAt': self.soldOutAt_1},
                {'soldOutAt': self.soldOutAt_2},
            ]
        }

        # Now
        hour = RELAUNCH_HOUR + 1
        minute = 1
        now = time(hour=hour, minute=minute, tzinfo=Eastern)

        expected = LaunchStatus.relaunchSoldOut
        result = _diff_launch_status(current, delta, now)
        self.assertEqual(result, expected)

    def test_launchStatus_relaunchSoldOut_right_before_reserve(self):
        current = self.load_deal(self.def_deal)
        current['launches'] = [
            {'soldOutAt': None},
            {'soldOutAt': None},
        ]
        current['launchStatus'] = LaunchStatus.relaunch.name
        current.pop('soldOutAt', None)

        # Changes
        delta = {
            'launches': [
                {'soldOutAt': None},
                {'soldOutAt': self.soldOutAt_2},
            ]
        }

        # Now
        hour = RESERVE_HOUR - 1
        minute = 59
        second = 59
        now = time(hour=hour, minute=minute, second=second, tzinfo=Eastern)

        expected = LaunchStatus.relaunchSoldOut
        result = _diff_launch_status(current, delta, now)
        self.assertEqual(result, expected)

    # .reserve

    def test_launchStatus_reserve_from_relaunchSoldOut(self):
        """ Transition: .relaunchSoldOut -> .reserve - 16:00.
        """
        current = self.load_deal(self.def_deal)
        current['launches'] = [
            {'soldOutAt': None},
            {'soldOutAt': self.soldOutAt_2},
        ]
        current['launchStatus'] = LaunchStatus.relaunchSoldOut.name
        current.pop('soldOutAt', None)

        # Changes
        delta = {}

        # Now
        hour = RESERVE_HOUR
        minute = 0
        second = 0
        now = time(hour=hour, minute=minute, second=second, tzinfo=Eastern)

        expected = LaunchStatus.reserve
        result = _diff_launch_status(current, delta, now)
        self.assertEqual(result, expected)

    # .soldOut

    def test_launchStatus_soldOut_1(self):
        current = self.load_deal(self.def_deal)
        current['launches'] = [
            {'soldOutAt': self.soldOutAt_1},
            {'soldOutAt': self.soldOutAt_2},
        ]
        current['launchStatus'] = LaunchStatus.reserve.name
        current.pop('soldOutAt', None)

        # Changes
        delta = {'soldOutAt': self.soldOutAt_3}

        # Now
        hour = RESERVE_HOUR
        minute = 1
        second = 0
        now = time(hour=hour, minute=minute, second=second, tzinfo=Eastern)

        expected = LaunchStatus.soldOut
        result = _diff_launch_status(current, delta, now)
        self.assertEqual(result, expected)

    # Exceptions

    def test_launchStatus_exception_1(self):
        # Missing launchStatus
        current = self.load_deal(self.def_deal)
        current.pop('launchStatus', None)

        delta = {}

        self.assertRaises(ValueError, _diff_launch_status, current, delta)

    def test_launchStatus_exception_2(self):
        # Malformed `launches`
        current = self.load_deal(self.def_deal)
        current['launches'] = []

        delta = {}

        self.assertRaises(ValueError, _diff_launch_status, current, delta)

    # ------------------------------------------------------------------------
    # Topic

    """
    def test_topic_TEMPLATE(self):
        current = self.load_deal(self.def_deal)
        current_topic = {
            'commentCount': 7,
            'createdAt': '2020-06-14T04:00:09.381Z',
            'id': '5ee5a0c9ee5dc612801231f7',
            'replyCount': 3,
            'url': 'https://meh.com/forum/topics/something',
            'voteCount': 0
        }
        current['topic'] = current_topic

        # Changes
        delta = {}

        update = copy.deepcopy(current)
        update_topic = copy.deepcopy(current_topic)
        update_topic.update(delta)
        update['topic'] = update_topic

        expected = delta

        result = _diff_topic(current, update)
        self.assertEqual(result, expected)
    """

    def test_topic_1(self):
        current = self.load_deal(self.def_deal)
        current_topic = {
            'commentCount': 7,
            'createdAt': '2020-06-14T04:00:09.381Z',
            'id': '5ee5a0c9ee5dc612801231f7',
            'replyCount': 3,
            'url': 'https://meh.com/forum/topics/something',
            'voteCount': 0
        }
        current['topic'] = current_topic

        # Changes
        delta = {
            'commentCount': 20
        }

        update = copy.deepcopy(current)
        update_topic = copy.deepcopy(current_topic)
        update_topic.update(delta)
        update['topic'] = update_topic

        expected = {
            'commentCount': 20,
            'createdAt': '2020-06-14T04:00:09.381Z',
            'id': '5ee5a0c9ee5dc612801231f7',
            'replyCount': 3,
            'url': 'https://meh.com/forum/topics/something',
            'voteCount': 0
        }

        result = _diff_topic(current, update)
        self.assertEqual(result, expected)

    # ------------------------------------------------------------------------
    # DealDelta

    def test_deal_delta_launch_status(self):
        launch_status = LaunchStatus.launchSoldOut
        delta = {
            'launchStatus': launch_status.name
        }

        expected = {
            DealDelta.launchStatus: launch_status
        }
        result = _diff_deal_delta(delta)
        self.assertEqual(result, expected)

    def test_deal_delta_comment_count(self):
        comment_count = 11
        delta = {
            'topic': {
                'commentCount': comment_count
            }
        }

        expected = {
            DealDelta.commentCount: comment_count
        }
        result = _diff_deal_delta(delta)
        self.assertEqual(result, expected)

    def test_deal_delta_both(self):
        comment_count = 1
        launch_status = LaunchStatus.relaunch
        delta = {
            'launchStatus': launch_status.name,
            'topic': {
                'commentCount': comment_count,
                'id': 'something_else'
            }
        }

        expected = {
            DealDelta.launchStatus: launch_status,
            DealDelta.commentCount: comment_count
        }
        result = _diff_deal_delta(delta)
        self.assertEqual(result, expected)

    # Exceptions

    def test_deal_delta_type_error(self):
        delta = {'launchStatus': 'invalid_status'}
        self.assertRaises(ValueError, _diff_deal_delta, delta)

    # def test_launchStatus_relaunch_2(self):
    #     current = self.load_deal(self.def_deal)
    #     current['launches'] = [
    #         {'soldOutAt': self.soldOutAt_1},
    #         {'soldOutAt': None},
    #     ]
    #     current['launchStatus'] = LaunchStatus.launch.name
    #     current.pop('soldOutAt', None)

    #     # Changes
    #     delta = {
    #         'launches': [
    #             {'soldOutAt': self.soldOutAt_1},
    #             {'soldOutAt': None},
    #         ]
    #     }

    #     # Now
    #     hour = PREMIER_HOUR + 4
    #     minute = 1
    #     now = time(hour=hour, minute=minute, tzinfo=Eastern)

    #     expected = LaunchStatus.launchSoldOut
    #     result = _diff_launch_status(current, delta, now)
    #     self.assertEqual(result, expected)

    # TODO: verify we only send a notification at relaunch if launch sold out
