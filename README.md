# Adequate-Backend

GraphQL backend for [Adequate](https://github.com/mgacy/Adequate), a free and open-source iOS client for the [Meh](https://meh.com) daily deal website.

## Setup

### Dependencies

- [amplify-cli](https://github.com/aws-amplify/amplify-cli)

- [aws-cli](https://github.com/aws/aws-cli/tree/v2)

- [aws-sam-cli](https://github.com/aws/aws-sam-cli)

- [boto3](https://github.com/boto/boto3)


### Clone project

```bash
git clone https://github.com/mgacy/Adequate-Backend.git
cd Adequate-Backend
```

### Deploy Amplify App

Initialize AppSync API:

```bash
amplify init
```

Deploy:

```bash
amplify push
```

### Create KMS Key

Create a customer managed KMS key to 

```bash
make init
```

### Environment Variables

#### Get Meh API Key

Obtain an API key from [meh](https://meh.com/developers-developers-developers) and paste as value for `PLAIN_API_KEY` in `.env` (this file will have been created by the `make init` command).

#### Alarm Email (optional)

`ALARM_EMAIL`: email address to which CloudWatch alarms for `deal_check` errors will be sent
