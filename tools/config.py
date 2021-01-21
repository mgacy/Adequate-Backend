class Config:

    # LOG_FORMAT = '%(levelname)s: %(asctime)s: %(message)s'

    # Default base name for AWS CloudFormation stacks
    DEFAULT_BASE_STACK_NAME = 'adequate-sam'

    # Relative path of amplify configuration file
    TEAM_PROVIDER_INFO = '../amplify/team-provider-info.json'

    # Relative path of amplify environment configuration file
    # AMPLIFY_META = '../amplify/#current-cloud-backend/amplify-meta.json'

    # Name of Amplify development environment and suffix for corresponding
    # CloudFormation stack
    DEV_BRANCH_SUFFIX = 'dev'

    # Name of Amplify production environment and suffix for corresponding
    # CloudFormation stack
    MASTER_BRANCH_SUFFIX = 'master'

    ################
    # AWS DynamoDB #
    ################

    # Name of GSI
    RECENT_INDEX_NAME = 'isRecent-createdAt-index'
    
    # TODO: use different values for master / develop?
    DEFAULT_READ_UNITS = 3  # 5?
    
    DEFAULT_WRITE_UNITS = 1  # 2?

    # BILLING_MODES = [
    #     'PROVISIONED',
    #     'PAY_PER_REQUEST'
    # ]

    ###########
    # AWS KMS #
    ###########

    # Alias for KMS customer master key
    KMS_ALIAS = 'adequate'

    # Description for KMS customer master key s
    KMS_DESCRIPTION = 'adequate assets'

    # ENV_VARS_PATH = 'env-vars.sh'

    ##############
    # AWS LAMBDA #
    ##############

    # Name of `deal_check` lambda for a given branch
    LAMBDA_DEAL_CHECK = '{base_name}-dealCheck-{aws_branch}'

    # Name of `push_notificaiton` lambda for a given branch
    LAMBDA_NOTIFICATION = '{base_name}-notification-{aws_branch}'

    ###########
    # AWS SNS #
    ###########

    # AWS SNS platform for APNs sandbox
    DEV_SNS_PLATFORM = 'APNS_SANDBOX'

    # Name of AWS SNS platform application using APNs sandbox
    DEV_SNS_APP_NAME = 'Adequate-Development'

    # AWS SNS platform for APNs
    MASTER_SNS_PLATFORM = 'APNS'

    # Name of AWS SNS platform application using APNs
    MASTER_SNS_APP_NAME = 'Adequate-Production'

    # Name of inline policy to attach to unauth IAM role
    SNS_POLICY_NAME = 'APNs_SNSAccess'

    # Valid AWS SNS platforms
    VALID_SNS_PLATFORMS = [DEV_SNS_PLATFORM, MASTER_SNS_PLATFORM]
