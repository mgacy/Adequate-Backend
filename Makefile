.SHELLFLAGS := -eu -o pipefail -c
MAKEFLAGS += --no-builtin-rules

ifneq (,$(wildcard ./.env))
	include .env
	export
endif

# Variables
BASE_NAME ?= adequate-sam
GRAPHQL_API_ID ?= "UNDEFINED"
GRAPHQL_ENDPOINT ?= "UNDEFINED"
KMS_KEY_ID ?= "UNDEFINED"
MEH_API_KEY ?= "UNDEFINED"
APNS_CATEGORY ?= "UNDEFINED"
ALARM_EMAIL ?= "NONE"

AMPLIFY_SETTINGS = amplify/\#current-cloud-backend/amplify-meta.json
AWS_REGION := $(shell jq -r '.providers.awscloudformation.Region' ${AMPLIFY_SETTINGS})
AWS_BRANCH := $(shell jq -r '.envName' amplify/.config/local-env-info.json)
GRAPHQL_API_ID := $(shell jq -r '.api[(.api | keys)[0]].output.GraphQLAPIIdOutput' ${AMPLIFY_SETTINGS})
GRAPHQL_ENDPOINT := $(shell jq -r '.api[(.api | keys)[0]].output.GraphQLAPIEndpointOutput' ${AMPLIFY_SETTINGS})

ifndef STACK_NAME
STACK_NAME = $(BASE_NAME)-$(AWS_BRANCH)
endif


help:
	$(info ${HELP_MESSAGE})
	@exit 0

deploy: ##=> Deploy services
	$(info [*] Building and deploying adequate service...)
	MEH_API_KEY=$(shell aws kms encrypt \
		--region $(AWS_REGION) \
		--key-id $(KMS_KEY_ID) \
		--plaintext $(PLAIN_API_KEY) \
		--encryption-context LambdaFunctionName=$(BASE_NAME)-dealCheck-$(AWS_BRANCH) \
		--cli-binary-format raw-in-base64-out \
		--output text \
		--query CiphertextBlob); \
	cd sam-app && \
		pipenv run sam build && \
		sam deploy \
			--region $(AWS_REGION) \
			--stack-name $(STACK_NAME) \
			--capabilities CAPABILITY_IAM \
			--parameter-overrides \
				BaseName=$(BASE_NAME) \
				Environment=$(AWS_BRANCH) \
				KmsKeyId=$(KMS_KEY_ID) \
				MehApiKey=$${MEH_API_KEY} \
				ApnsCategory=$(APNS_CATEGORY) \
				GraphQlId=$(GRAPHQL_API_ID) \
				GraphQlEndpoint=$(GRAPHQL_ENDPOINT) \
				AlarmEmailParam=$(ALARM_EMAIL)

deploy.guided: ##=> Deploy services
	$(info [*] Building and deploying adequate service...)
	MEH_API_KEY=$(shell aws kms encrypt \
		--region $(AWS_REGION) \
		--key-id $(KMS_KEY_ID) \
		--plaintext $(PLAIN_API_KEY) \
		--encryption-context LambdaFunctionName=$(BASE_NAME)-dealCheck-$(AWS_BRANCH) \
		--cli-binary-format raw-in-base64-out \
		--output text \
		--query CiphertextBlob); \
	cd sam-app && \
		pipenv run sam build && \
		sam deploy \
			--guided \
			--region $(AWS_REGION) \
			--stack-name $(STACK_NAME) \
			--capabilities CAPABILITY_IAM \
			--parameter-overrides \
				BaseName=$(BASE_NAME) \
				Environment=$(AWS_BRANCH) \
				KmsKeyId=$(KMS_KEY_ID) \
				MehApiKey=$${MEH_API_KEY} \
				ApnsCategory=$(APNS_CATEGORY) \
				GraphQlId=$(GRAPHQL_API_ID) \
				GraphQlEndpoint=$(GRAPHQL_ENDPOINT) \
				AlarmEmailParam=$(ALARM_EMAIL)

dev: ##=> Install dependencies for SAM app
	cd sam-app && \
		make dev

configure.kms: ##=> Create KMS customer master key
	$(info [*] Creating KMS master key ...)
	source sam-app/.venv/bin/activate && \
		python tools/configure_kms.py

configure.gsi: ##=> Create DynamoDB GSI for AppSync Query.dealHistory
	$(info [*] Configuring GSI for Query.dealHistory in Table 'Deal-$(GRAPHQL_API_ID)-$(AWS_BRANCH)')
	source sam-app/.venv/bin/activate && \
		python tools/configure_index.py Deal-$(GRAPHQL_API_ID)-$(AWS_BRANCH)

init: ##=> Install SAM dependencies and configure additional components
	$(MAKE) dev
	$(MAKE) configure.kms
	$(MAKE) configure.gsi

notifications: ##=> Create SNS Platform Applications
	$(info [*] Creating SNS Platform Applications...)
	source sam-app/.venv/bin/activate && \
		python tools/configure_sns.py

.PHONY: help init deploy dev configure.kms configure.gsi init notifications

#############
#  Helpers  #
#############

define HELP_MESSAGE

	Environment variables:

	AWS_BRANCH: "dev"
		Description: Feature branch name used as part of stacks name
	STACK_NAME: "adequate-sam-<branch>"
		Description: Stack Name already deployed; used for dirty/individual deployment
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
	ALARM_EMAIL: Email address
		Description: Email address to which lambda function error notifications are sent

	Common usage:

	...::: Create S3 bucket :::...
	$ make create-bucket

	...::: Deploy all SAM-based services :::...
	$ make deploy

	...::: Install SAM dependencies and configure additional components :::...
	$ make init

	...::: Create SNS Platform Applications of APNs :::...
	$ make notifications
endef
