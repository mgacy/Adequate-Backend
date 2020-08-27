.SHELLFLAGS := -eu -o pipefail -c
MAKEFLAGS += --warn-undefined-variables
MAKEFLAGS += --no-builtin-rules

# Variables
BASE_NAME ?= adequate-sam
GRAPHQL_API_ID ?= "UNDEFINED"
GRAPHQL_ENDPOINT ?= "UNDEFINED"
KMS_KEY_ID ?= "UNDEFINED"
MEH_API_KEY ?= "UNDEFINED"
APNS_CATEGORY ?= "UNDEFINED"

AMPLIFY_SETTINGS = amplify/\#current-cloud-backend/amplify-meta.json
AWS_REGION := $(shell jq -r '.providers.awscloudformation.Region' ${AMPLIFY_SETTINGS})
AWS_BRANCH := $(shell jq -r '.envName' amplify/.config/local-env-info.json)
GRAPHQL_API_ID := $(shell jq -r '.api[(.api | keys)[0]].output.GraphQLAPIIdOutput' ${AMPLIFY_SETTINGS})
GRAPHQL_ENDPOINT := $(shell jq -r '.api[(.api | keys)[0]].output.GraphQLAPIEndpointOutput' ${AMPLIFY_SETTINGS})

ifndef STACK_NAME
STACK_NAME = $(BASE_NAME)-$(AWS_BRANCH)
endif

ifndef DEPLOYMENT_BUCKET_NAME
DEPLOYMENT_BUCKET_NAME = $(BASE_NAME)-$(AWS_BRANCH)-src-$(AWS_REGION)
endif


help:
	$(info ${HELP_MESSAGE})
	@exit 0

create-bucket: ##=> Create S3 bucket
	$(info [*] Creating S3 bucket at s3://$(DEPLOYMENT_BUCKET_NAME)")
	@aws s3 mb s3://$(DEPLOYMENT_BUCKET_NAME) --region $(AWS_REGION)

deploy: ##=> Deploy services
	$(info [*] Building and deploying adequate service...)
	cd sam-app && \
		sam build && \
		sam deploy \
			--s3-bucket $(DEPLOYMENT_BUCKET_NAME) \
			--region $(AWS_REGION) \
			--stack-name $(STACK_NAME) \
			--capabilities CAPABILITY_IAM \
			--parameter-overrides \
				BaseName=$(BASE_NAME) \
				Environment=$(AWS_BRANCH) \
				KmsKeyId=$(KMS_KEY_ID) \
				MehApiKey=$(MEH_API_KEY) \
				ApnsCategory=$(APNS_CATEGORY) \
				GraphQlId=$(GRAPHQL_API_ID) \
				GraphQlEndpoint=$(GRAPHQL_ENDPOINT)

configure-gsi:
	$(info [*] Configuring GSI for Query.dealHistory in Table 'Deal-$(GRAPHQL_API_ID)-$(AWS_BRANCH)')
	python tools/configure_index.py Deal-$(GRAPHQL_API_ID)-$(AWS_BRANCH)

.PHONY: help create-bucket deploy configure-gsi

#############
#  Helpers  #
#############

define HELP_MESSAGE

	Environment variables:

	AWS_BRANCH: "dev"
		Description: Feature branch name used as part of stacks name
	STACK_NAME: "adequate-sam-<branch>"
		Description: Stack Name already deployed; used for dirty/individual deployment
	DEPLOYMENT_BUCKET_NAME: "a_valid_bucket_name"
		Description: S3 Bucket name used for deployment artifacts
	GRAPHQL_API_ID: "hnxochcn4vfdbgp6zaopgcxk2a"
		Description: AppSync GraphQL ID already deployed
	GRAPHQL_ENDPOINT: "https://<api_id>.appsync-api.<region>.amazonaws.com/graphql"
		Description: AppSync GraphQL endpoint already deployed
	KMS_KEY_ID: "a_valid_key_id"
		Description: AWS KMS key id used to encrypt meh API key
	MEH_API_KEY: "a_valid_api_key"
		Description: Meh API key from https://meh.com/developers-developers-developers
	APNS_CATEGORY: "MGDailyDealCategory"
		Description: Notification category used for APNs

	Common usage:

	...::: Create S3 bucket :::...
	$ make create-bucket

	...::: Deploy all SAM based services :::...
	$ make deploy

	...::: Configure GSI for Query.dealHistory :::...
	$ make configure-gsi
endef
