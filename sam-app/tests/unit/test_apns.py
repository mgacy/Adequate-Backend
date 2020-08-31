import unittest
from .mocks import BotoSessionMock
from push_notification import apns


class APNSTestCase(unittest.TestCase):

    def_apns_category = 'MGDailyDealCategory'

    # def setUp(self):

    # def tearDown(self):

    # push_notification

    # push_background

    # make_new_deal_message

    # make_delta_message

    def test_make_delta_comment_1(self):
        deal_id = 'a6k5A000000kP9LQAU'
        delta_type = 'commentCount'
        delta_value = 5
        
        message = {
            'id': deal_id,
            'delta_type': delta_type,
            'delta_value': delta_value
        }

        expected = (
            '{"aps": {"content-available": 1}, '
            '"deal-id": "a6k5A000000kP9LQAU", '
            '"delta-type": "commentCount", '
            '"delta-value": 5}'
        )

        result = apns.make_delta_message(message)
        self.assertEqual(result, expected)

    def test_make_delta_status_1(self):
        deal_id = 'a6k5A000000kP9LQAU' 
        delta_type = 'launchStatus'
        delta_value = 'launch'
        
        message = {
            'id': deal_id,
            'delta_type': delta_type,
            'delta_value': delta_value
        }

        expected = (
            '{"aps": {"content-available": 1}, '
            '"deal-id": "a6k5A000000kP9LQAU", '
            '"delta-type": "launchStatus", '
            '"delta-value": "launch"}'
        )
        
        result = apns.make_delta_message(message)
        self.assertEqual(result, expected)

    # publish_message

    def test_publish_delta_status_prod(self):
        message = (
            '{"aps": {"content-available": 1}, '
            '"deal-id": "a6k5A000000kP9LQAU", '
            '"delta-type": "launchStatus", '
            '"delta-value": "launch"}'
        )

        # deal_id = 'a6k5A000000kP9LQAU' 
        # delta_type = 'launchStatus'
        # delta_value = 'launch'
        # message = (
        #     '{"aps": {"content-available": 1}, '
        #     f'"deal-id": "{deal_id}", '
        #     f'"delta-type": "{delta_type}", '
        #     f'"delta-value": "{delta_value}"'
        #     '}'
        # )

        session = BotoSessionMock()
        default_message='default message'
        apns_server = 'prod'
        apns.publish_message(session, 
                             topic_arn='fake_topic_arn',
                             apns_server=apns_server,
                             apns_message=message,
                             default_message=default_message)

        expected = (
            '{'
            '"default": "default message", '
            '"APNS": "{'
            '\\"aps\\": {'
            '\\"content-available\\": 1'
            '}, '
            '\\"deal-id\\": \\"a6k5A000000kP9LQAU\\", '
            '\\"delta-type\\": \\"launchStatus\\", '
            '\\"delta-value\\": \\"launch\\"'
            '}"'
            '}'
        )

        result = session.client.message
        self.assertEqual(result, expected)

    def test_publish_delta_status_dev(self):
        message = (
            '{"aps": {"content-available": 1}, '
            '"deal-id": "a6k5A000000kP9LQAU", '
            '"delta-type": "launchStatus", '
            '"delta-value": "launch"}'
        )

        session = BotoSessionMock()
        default_message='default message'
        apns_server = 'dev'
        apns.publish_message(session, 
                             topic_arn='fake_topic_arn',
                             apns_server=apns_server,
                             apns_message=message,
                             default_message=default_message)

        expected = (
            '{'
            '"default": "default message", '
            '"APNS_SANDBOX": "{'
            '\\"aps\\": {'
            '\\"content-available\\": 1'
            '}, '
            '\\"deal-id\\": \\"a6k5A000000kP9LQAU\\", '
            '\\"delta-type\\": \\"launchStatus\\", '
            '\\"delta-value\\": \\"launch\\"'
            '}"'
            '}'
        )

        result = session.client.message
        self.assertEqual(result, expected)

    def test_publish_delta_status_both(self):
        message = (
            '{"aps": {"content-available": 1}, '
            '"deal-id": "a6k5A000000kP9LQAU", '
            '"delta-type": "launchStatus", '
            '"delta-value": "launch"}'
        )

        session = BotoSessionMock()
        default_message='default message'
        apns_server = 'both'
        apns.publish_message(session, 
                             topic_arn='fake_topic_arn',
                             apns_server=apns_server,
                             apns_message=message,
                             default_message=default_message)

        expected = (
            '{'
            '"default": "default message", '
            '"APNS": "{'
            '\\"aps\\": {'
            '\\"content-available\\": 1'
            '}, '
            '\\"deal-id\\": \\"a6k5A000000kP9LQAU\\", '
            '\\"delta-type\\": \\"launchStatus\\", '
            '\\"delta-value\\": \\"launch\\"'
            '}", '
            '"APNS_SANDBOX": "{'
            '\\"aps\\": {'
            '\\"content-available\\": 1'
            '}, '
            '\\"deal-id\\": \\"a6k5A000000kP9LQAU\\", '
            '\\"delta-type\\": \\"launchStatus\\", '
            '\\"delta-value\\": \\"launch\\"'
            '}"'
            '}'
        )

        result = session.client.message
        self.assertEqual(result, expected)

    def test_publish_invalid_server(self):
        session = BotoSessionMock()
        topic_arn='fake_topic_arn'
        apns_server = 'meh'
        apns_message ='{"aps": {"content-available": 1}'
        default_message='default message'

        self.assertRaises(
            ValueError, apns.publish_message, session, topic_arn, apns_server, apns_message, default_message)

    # _make_background_notification

    def test_make_background_notification_no_additional(self):
        additional = None

        expected = {
            'aps': {
                'content-available': 1
            }
        }

        result = apns._make_background_notification(additional)
        self.assertEqual(result, expected)

    def test_make_background_notification_with_additional(self):
        deal_id = 'a6k5A000000kP9LQAU'
        delta_type = 'commentCount'
        delta_value = 5

        additional = {
            'id': deal_id,
            'delta_type': delta_type,
            'delta_value': delta_value
        }

        expected = {
            'aps': {
                'content-available': 1
            },
            'id': deal_id,
            'delta_type': delta_type,
            'delta_value': delta_value
        }

        result = apns._make_background_notification(additional)
        self.assertDictEqual(result, expected)

    # _make_notification

    # def test_make_notification_1(self):

    # raise_for_status
