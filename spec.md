this folder contains the codebase for two different Chalice apps:

- add.dctech.event is an event submission tool currently used with dctech.events
- dctech-newsletter handles newsletter subscriptions for dctech.events

I'd like to rebuild these into a single Flask app that can be installed on any Linux VPS, and they should share a common "site" construct, of which dctech.events is one. There should be no need for data storage beyond the mechanisms already in use, DynamoDB, GitHub, and the AWS SES service. Any frontend code should use HTMX, so any backend API's should return HTML, not JSON. Assume it will be deployed to an EC2 instance with a role that allows it access to the neccessary AWS services.
