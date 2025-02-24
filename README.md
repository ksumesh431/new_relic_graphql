# New Relic Data Integration and Mapping

## Overview

This project automates the process of fetching, processing, and mapping data from the New Relic NerdGraph API. The goal is to combine multiple datasets (workflows, alert policies, NRQL conditions, channels, and destinations) into a single, comprehensive CSV file that provides a unified view of workflows, their associated alert policies, and their destination channels.

The project involves multiple GraphQL queries to fetch data from New Relic's API, processes the data to map relationships between entities, and outputs the final result in a structured CSV format.

---

## Why Multiple Queries?

New Relic's data is structured in a way that requires multiple queries to fetch and combine related information. Each query targets a specific dataset, and the relationships between these datasets are not directly available in a single query. Here's why multiple queries are necessary:

1. **Alert Policies and NRQL Conditions**:
   - Alert policies define the rules for monitoring and alerting.
   - NRQL conditions are specific conditions under these policies that trigger alerts.
   - These two datasets are related but need to be fetched separately and then mapped together.

2. **Workflows**:
   - Workflows define how alerts are routed to specific destinations (e.g., Slack, PagerDuty).
   - Each workflow can have multiple destination channels, which are identified by `channelId`.

3. **Channels and Destinations**:
   - Channels represent the communication endpoints (e.g., Slack channels, email addresses).
   - Destinations provide additional metadata about these channels (e.g., email addresses, webhook URLs).
   - Channels and destinations are related by `destinationId`.

4. **Mapping Relationships**:
   - The final output requires mapping workflows to their associated alert policies and NRQL conditions, and then further mapping these workflows to their destination channels and metadata.

---

## Complexity of the Process

The complexity arises from the hierarchical and relational nature of the data:

1. **Hierarchical Relationships**:
   - Alert policies contain NRQL conditions.
   - Workflows reference destination channels.
   - Channels reference destinations.

2. **One-to-Many Relationships**:
   - A single workflow can have multiple destination channels.
   - A single destination can be associated with multiple channels.

3. **Data Enrichment**:
   - The final output requires enriching workflows with data from alert policies, NRQL conditions, and destination metadata.

4. **Pagination**:
   - New Relic's API uses pagination for large datasets, requiring the use of `nextCursor` to fetch all data.

---

## Final Output

The final output is a CSV file named `workflows_with_channels.csv`. This file combines data from all the queries and provides a unified view of workflows, their associated alert policies, NRQL conditions, and destination channels.

### Columns in the Final CSV

| Column Name                          | Description                                                                 |
|--------------------------------------|-----------------------------------------------------------------------------|
| `workflow_name`                      | The name of the workflow.                                                  |
| `workflow_id`                        | The unique ID of the workflow.                                             |
| `destination_channel_ids`            | A comma-separated list of channel IDs associated with the workflow.        |
| `alert_policy_name`                  | The name of the alert policy associated with the workflow.                 |
| `alert_policy_id`                    | The unique ID of the alert policy.                                         |
| `nrql_condition_id`                  | The unique ID of the NRQL condition under the alert policy.                |
| `alert_condition_name`               | The name of the NRQL condition.                                            |
| `nrql_query`                         | The NRQL query associated with the condition.                              |
| `nrql_condition`                     | A detailed description of the NRQL condition (e.g., thresholds, operators).|
| `attribute.accumulations.policyName` | The policy name if the workflow uses accumulations (optional).             |
| `attribute.labels.policyIds`         | The policy IDs associated with the workflow.                               |
| `policy.operator`                    | The operator used in the workflow's filter.                                |
| `policy.values`                      | The values used in the workflow's filter.                                  |
| `channel_id`                         | The unique ID of the destination channel.                                  |
| `destination_channel_name`           | The name of the destination channel.                                       |
| `destination_channel_type`           | The type of the destination channel (e.g., Slack, PagerDuty).              |
| `destination_id`                     | The unique ID of the destination associated with the channel.              |
| `destination_key`                    | The key of the destination property (e.g., `email`, `url`).                |
| `destination_value`                  | The value of the destination property (e.g., email address, webhook URL).  |

---

## How the Code Works

The code is divided into two main parts:

### Part 1: Fetch and Process Data
1. **Fetch Alert Policies and NRQL Conditions**:
   - Queries the API to fetch alert policies and their associated NRQL conditions.
   - Maps the policies and conditions together.
   - Outputs the result to `workflows_with_alert_policies.csv`.

2. **Fetch Channels and Destinations**:
   - Queries the API to fetch channels and their associated destinations.
   - Maps channels to destinations and filters destination properties to include only `email` and `url`.
   - Outputs the result to `channels_and_destinations.csv`.

### Part 2: Map Workflows with Channels
1. **Load Intermediate Data**:
   - Loads `workflows_with_alert_policies.csv` and `channels_and_destinations.csv`.

2. **Map Relationships**:
   - Maps workflows to their destination channels using `channelId`.
   - Enriches workflows with data from alert policies, NRQL conditions, and destination metadata.

3. **Output Final CSV**:
   - Outputs the final result to `workflows_with_channels.csv`.

---

## How to Run the Code

1. **Set Up Environment Variables**:
   - Create a `.env` file in the project directory with the following variables:
     ```
     NEW_RELIC_API_KEY=your_api_key
     NEW_RELIC_ACCOUNT_ID=your_account_id
     ```

2. **Install Dependencies**:
   - Install the required Python packages:
     ```bash
     pip install requests python-dotenv
     ```

3. **Run the Script**:
   - Execute the script:
     ```bash
     python script_name.py
     ```

4. **Output Files**:
   - The script will generate the following files:
     - `workflows_with_alert_policies.csv`
     - `channels_and_destinations.csv`
     - `workflows_with_channels.csv`

---

## Example Use Case

Imagine you are managing a large-scale monitoring system with multiple workflows, alert policies, and communication channels. You need a single view that shows:

- Which workflows are associated with which alert policies.
- The NRQL conditions that trigger alerts.
- The destination channels (e.g., Slack, PagerDuty) where alerts are sent.
- Metadata about these channels (e.g., email addresses, webhook URLs).

This script automates the entire process, saving you hours of manual work and ensuring data accuracy.

---

## Limitations

1. **API Rate Limits**:
   - The script relies on New Relic's API, which may have rate limits. If you encounter issues, consider adding delays between requests.

2. **Data Completeness**:
   - The script assumes that all relationships (e.g., `channelId`, `destinationId`) are correctly configured in New Relic. Missing or incorrect data in the API response may affect the output.

3. **Scalability**:
   - For very large datasets, the script may take time to process due to pagination and data mapping.
