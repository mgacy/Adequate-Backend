
class BotoMockBase(object):

    base_response = {
        'ResponseMetadata': {
            'RequestId': '1234567890ABCDEF',
            'HostId': 'host ID data will appear here as a hash',
            'HTTPStatusCode': 200,
            'HTTPHeaders': {'header metadata key/values will appear here'},
            'RetryAttempts': 0
        }
    }

    error_response = {
        'Error': {
            'Code': 'SomeServiceException',
            'Message': 'Details/context around the exception or error'
        },
        'ResponseMetadata': {
            'RequestId': '1234567890ABCDEF',
            'HostId': 'host ID data will appear here as a hash',
            'HTTPStatusCode': 400,
            'HTTPHeaders': {'header metadata key/values will appear here'},
            'RetryAttempts': 0
        }
    }

    def __repr__(self):
        return '{0})'.format(self.__class__.__name__)

    def build_response(self, additional):
        return { **self.base_response, **additional}

    def build_error_response(self, additional):
        return { **self.error_response, **additional}


class SNSClientMock(BotoMockBase):

    def publish(
        self, 
        TopicArn='string',
        TargetArn='string',
        PhoneNumber='string',
        Message='string',
        Subject='string',
        MessageStructure='string',
        MessageAttributes={}
   ):
        self.topic_arn = TopicArn
        self.message = Message
        self.message_structure = MessageStructure
        return self.build_response({'MessageId': 'some_message_id'})


class BotoSessionMock(object):

    def __init__(
        self, 
        aws_access_key_id=None, 
        aws_secret_access_key=None, 
        aws_session_token=None,
        region_name='us-west-2',
        botocore_session=None, 
        profile_name=None
    ):
        self.access_key = aws_access_key_id
        self.secret_key = aws_secret_access_key
        self.token = aws_session_token
        self.region_name = region_name
        self.botocore_session = botocore_session
        self.profile_name = profile_name

    def __repr__(self):
        return '{0}(region_name={1})'.format(
            self.__class__.__name__, self.region_name)

    def client(
        self, 
        service_name,
        region_name=None, 
        api_version=None, 
        use_ssl=True, 
        verify=None, 
        endpoint_url=None, 
        aws_access_key_id=None, 
        aws_secret_access_key=None, 
        aws_session_token=None, 
        config=None
    ):
        if service_name == 'sns':
            # return SNSClientMock()
            self.client = SNSClientMock()
            return self.client
        else:
            raise ValueError('Unsupported service')

    # def get_credentials(self):
    #     return CredentialMock()
