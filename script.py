import os
import requests
import csv
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get API key and account ID from environment variables
API_KEY = os.environ.get("NEW_RELIC_API_KEY")
ACCOUNT_ID = os.environ.get("NEW_RELIC_ACCOUNT_ID")

# GraphQL Endpoint
NRQL_ENDPOINT = "https://api.newrelic.com/graphql"
HEADERS = {"Content-Type": "application/json", "API-Key": API_KEY}


def fetch_data(query, variables=None):
    """Fetch data from the New Relic NerdGraph API."""
    response = requests.post(
        NRQL_ENDPOINT, json={"query": query, "variables": variables}, headers=HEADERS
    )
    response.raise_for_status()
    return response.json()


def get_alert_policies_and_conditions():
    """Fetch alert policies and NRQL conditions."""
    # Fetch alert policies
    policies = []
    cursor = ""
    while True:
        query = """
        query($accountId: Int!, $cursor: String) {
          actor {
            account(id: $accountId) {
              alerts {
                policiesSearch(cursor: $cursor) {
                  policies {
                    id
                    name
                    incidentPreference
                  }
                  nextCursor
                }
              }
            }
          }
        }
        """
        variables = {"accountId": int(ACCOUNT_ID), "cursor": cursor}
        data = fetch_data(query, variables)
        result = data["data"]["actor"]["account"]["alerts"]["policiesSearch"]
        policies.extend(result["policies"])
        cursor = result["nextCursor"]
        if not cursor:
            break

    # Fetch NRQL conditions
    nrql_conditions = []
    cursor = ""
    while True:
        query = """
        query($accountId: Int!, $cursor: String) {
          actor {
            account(id: $accountId) {
              alerts {
                nrqlConditionsSearch(cursor: $cursor) {
                  nrqlConditions {
                    policyId
                    id
                    type
                    name
                    nrql {
                      query
                    }
                    terms {
                      operator
                      priority
                      threshold
                      thresholdDuration
                      thresholdOccurrences
                    }
                  }
                  nextCursor
                }
              }
            }
          }
        }
        """
        variables = {"accountId": int(ACCOUNT_ID), "cursor": cursor}
        data = fetch_data(query, variables)
        result = data["data"]["actor"]["account"]["alerts"]["nrqlConditionsSearch"]
        nrql_conditions.extend(result["nrqlConditions"])
        cursor = result["nextCursor"]
        if not cursor:
            break

    # Map policies to NRQL conditions
    policy_dict = {policy["id"]: policy for policy in policies}
    mapped_data = []
    for condition in nrql_conditions:
        policy_id = condition["policyId"]
        if policy_id in policy_dict:
            policy = policy_dict[policy_id]
            mapped_data.append(
                {
                    "alert_policy_name": policy["name"],
                    "alert_policy_id": policy["id"],
                    "nrql_condition_id": condition["id"],
                    "alert_condition_name": condition[
                        "name"
                    ],  # Include the condition name
                    "nrql_query": condition["nrql"]["query"],
                    "nrql_condition": "; ".join(
                        [
                            f"operator: {term['operator']}, priority: {term['priority']}, "
                            f"threshold: {term['threshold']}, duration: {term['thresholdDuration']}, "
                            f"occurrences: {term['thresholdOccurrences']}"
                            for term in condition["terms"]
                        ]
                    ),
                }
            )
    return mapped_data


def get_workflows():
    """Fetch all workflows with pagination."""
    workflows = []
    cursor = ""
    while True:
        query = """
        query($accountId: Int!, $cursor: String) {
          actor {
            account(id: $accountId) {
              aiWorkflows {
                workflows(cursor: $cursor) {
                  entities {
                    id
                    name
                    destinationConfigurations {
                      channelId
                      name
                      notificationTriggers
                      type
                      updateOriginalMessage
                    }
                    issuesFilter {
                      predicates {
                        attribute
                        operator
                        values
                      }
                    }
                  }
                  nextCursor
                }
              }
            }
          }
        }
        """
        variables = {"accountId": int(ACCOUNT_ID), "cursor": cursor}
        data = fetch_data(query, variables)
        result = data["data"]["actor"]["account"]["aiWorkflows"]["workflows"]
        workflows.extend(result["entities"])
        cursor = result["nextCursor"]
        if not cursor:
            break
    return workflows


def process_workflows(workflows, alert_policies):
    """Process workflows and map them with alert policies."""
    processed_data = []

    # Create a dictionary of alert policies for quick lookup
    alert_policy_dict = {policy["alert_policy_id"]: policy for policy in alert_policies}

    for workflow in workflows:
        workflow_name = workflow["name"]
        workflow_id = workflow["id"]

        # Extract channel IDs from destinationConfigurations
        destination_channel_ids = [
            config["channelId"] for config in workflow["destinationConfigurations"]
        ]

        # Extract issuesFilter predicates
        if "issuesFilter" in workflow and workflow["issuesFilter"]:
            for predicate in workflow["issuesFilter"]["predicates"]:
                attribute = predicate["attribute"]
                if attribute == "labels.policyIds":
                    # Map policy IDs to alert policies
                    for policy_id in predicate["values"]:
                        if policy_id in alert_policy_dict:
                            alert_policy = alert_policy_dict[policy_id]
                            processed_data.append(
                                {
                                    "workflow_name": workflow_name,
                                    "workflow_id": workflow_id,
                                    "destination_channel_ids": ", ".join(
                                        destination_channel_ids
                                    ),
                                    "alert_policy_name": alert_policy[
                                        "alert_policy_name"
                                    ],
                                    "alert_policy_id": alert_policy["alert_policy_id"],
                                    "nrql_condition_id": alert_policy[
                                        "nrql_condition_id"
                                    ],
                                    "alert_condition_name": alert_policy[
                                        "alert_condition_name"
                                    ],  # Include the condition name
                                    "nrql_query": alert_policy["nrql_query"],
                                    "nrql_condition": alert_policy["nrql_condition"],
                                    "attribute.accumulations.policyName": None,
                                    "attribute.labels.policyIds": policy_id,
                                    "policy.operator": predicate["operator"],
                                    "policy.values": predicate["values"],
                                }
                            )
                elif attribute == "accumulations.policyName":
                    # Keep rows with accumulations.policyName unchanged
                    processed_data.append(
                        {
                            "workflow_name": workflow_name,
                            "workflow_id": workflow_id,
                            "destination_channel_ids": ", ".join(
                                destination_channel_ids
                            ),
                            "alert_policy_name": None,
                            "alert_policy_id": None,
                            "nrql_condition_id": None,
                            "alert_condition_name": None,
                            "nrql_query": None,
                            "nrql_condition": None,
                            "attribute.accumulations.policyName": predicate["values"],
                            "attribute.labels.policyIds": None,
                            "policy.operator": predicate["operator"],
                            "policy.values": predicate["values"],
                        }
                    )

    return processed_data


def get_channels_and_destinations():
    """Fetch channels and destinations with pagination."""
    channels = []
    destinations = []
    cursor = ""

    # Fetch channels
    while True:
        query = """
        query($accountId: Int!, $cursor: String) {
          actor {
            account(id: $accountId) {
              aiNotifications {
                channels(cursor: $cursor) {
                  entities {
                    id
                    name
                    type
                    destinationId
                    product
                  }
                  nextCursor
                }
              }
            }
          }
        }
        """
        variables = {"accountId": int(ACCOUNT_ID), "cursor": cursor}
        data = fetch_data(query, variables)
        result = data["data"]["actor"]["account"]["aiNotifications"]["channels"]
        channels.extend(result["entities"])
        cursor = result["nextCursor"]
        if not cursor:
            break

    # Fetch destinations
    query = """
    query($accountId: Int!) {
      actor {
        account(id: $accountId) {
          aiNotifications {
            destinations {
              entities {
                properties {
                  key
                  value
                }
                id
                name
              }
            }
          }
        }
      }
    }
    """
    variables = {"accountId": int(ACCOUNT_ID)}
    data = fetch_data(query, variables)
    destinations = data["data"]["actor"]["account"]["aiNotifications"]["destinations"][
        "entities"
    ]

    return channels, destinations


def map_channels_to_destinations(channels, destinations):
    """Map channels to destinations and filter destination properties."""
    mapped_data = []

    # Create a dictionary of destinations for quick lookup
    destination_dict = {destination["id"]: destination for destination in destinations}

    for channel in channels:
        destination_id = channel["destinationId"]
        channel_type = channel["type"]

        # Check if the destination exists
        if destination_id in destination_dict:
            destination = destination_dict[destination_id]
            # Filter properties to include only "email" or "url"
            filtered_properties = [
                prop
                for prop in destination["properties"]
                if prop["key"] in ["email", "url"]
            ]
            # If there are filtered properties, create rows for each
            if filtered_properties:
                for prop in filtered_properties:
                    mapped_data.append(
                        {
                            "channel_id": channel["id"],
                            "channel_name": channel["name"],
                            "channel_type": channel_type,
                            "destination_id": destination_id,
                            "destination_key": prop["key"],
                            "destination_value": prop["value"],
                        }
                    )
            else:
                # If no filtered properties, add a row with empty destination_key and destination_value
                mapped_data.append(
                    {
                        "channel_id": channel["id"],
                        "channel_name": channel["name"],
                        "channel_type": channel_type,
                        "destination_id": destination_id,
                        "destination_key": None,
                        "destination_value": None,
                    }
                )
        else:
            # If no destination exists, add a row with empty destination fields
            mapped_data.append(
                {
                    "channel_id": channel["id"],
                    "channel_name": channel["name"],
                    "channel_type": channel_type,
                    "destination_id": destination_id,
                    "destination_key": None,
                    "destination_value": None,
                }
            )

    return mapped_data


def write_to_csv(data, filename):
    """Write the processed data to a CSV file."""
    with open(filename, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)


def generate_workflows_with_alert_policies():
    print("Fetching alert policies and NRQL conditions...")
    alert_policies = get_alert_policies_and_conditions()
    print(f"Fetched {len(alert_policies)} alert policies and conditions.")

    print("Fetching workflows...")
    workflows = get_workflows()
    print(f"Fetched {len(workflows)} workflows.")

    print("Processing workflows and mapping with alert policies...")
    processed_data = process_workflows(workflows, alert_policies)
    print(f"Processed {len(processed_data)} rows.")

    print("Writing workflows_with_alert_policies.csv...")
    write_to_csv(processed_data, "workflows_with_alert_policies.csv")
    print("Data written to 'workflows_with_alert_policies.csv'.")


def generate_channels_and_destinations():
    print("Fetching channels and destinations...")
    channels, destinations = get_channels_and_destinations()
    print(f"Fetched {len(channels)} channels and {len(destinations)} destinations.")

    print("Mapping channels to destinations...")
    mapped_data = map_channels_to_destinations(channels, destinations)
    print(f"Mapped {len(mapped_data)} rows.")

    print("Writing channels_and_destinations.csv...")
    write_to_csv(mapped_data, "channels_and_destinations.csv")
    print("Data written to 'channels_and_destinations.csv'.")


################################################  End of first part ################################################


# Part 2: Generate workflows_with_channels.csv
def map_workflows_with_channels(workflows_data, channels_data):
    """Map workflows with channels and destinations."""
    mapped_data = []

    # Create a dictionary for quick lookup of channel data by channel_id
    channel_dict = {channel["channel_id"]: channel for channel in channels_data}

    for workflow in workflows_data:
        # Split destination_channel_ids into a list
        destination_channel_ids = workflow["destination_channel_ids"].split(", ")

        for channel_id in destination_channel_ids:
            if channel_id in channel_dict:
                channel = channel_dict[channel_id]
                # Add a new row for each channel_id
                mapped_data.append(
                    {
                        "workflow_name": workflow["workflow_name"],
                        "workflow_id": workflow["workflow_id"],
                        "destination_channel_ids": workflow["destination_channel_ids"],
                        "alert_policy_name": workflow["alert_policy_name"],
                        "alert_policy_id": workflow["alert_policy_id"],
                        "nrql_condition_id": workflow["nrql_condition_id"],
                        "alert_condition_name": workflow[
                            "alert_condition_name"
                        ],  # Include the condition name
                        "nrql_query": workflow["nrql_query"],
                        "nrql_condition": workflow["nrql_condition"],
                        "attribute.accumulations.policyName": workflow[
                            "attribute.accumulations.policyName"
                        ],
                        "attribute.labels.policyIds": workflow[
                            "attribute.labels.policyIds"
                        ],
                        "policy.operator": workflow["policy.operator"],
                        "policy.values": workflow["policy.values"],
                        "channel_id": channel["channel_id"],
                        "destination_channel_name": channel["channel_name"],
                        "destination_channel_type": channel["channel_type"],
                        "destination_id": channel["destination_id"],
                        "destination_key": channel["destination_key"],
                        "destination_value": channel["destination_value"],
                    }
                )
            else:
                # If channel_id is not found in channels_data, add a row with empty channel fields
                mapped_data.append(
                    {
                        "workflow_name": workflow["workflow_name"],
                        "workflow_id": workflow["workflow_id"],
                        "destination_channel_ids": workflow["destination_channel_ids"],
                        "alert_policy_name": workflow["alert_policy_name"],
                        "alert_policy_id": workflow["alert_policy_id"],
                        "nrql_condition_id": workflow["nrql_condition_id"],
                        "alert_condition_name": workflow[
                            "alert_condition_name"
                        ],  # Include the condition name
                        "nrql_query": workflow["nrql_query"],
                        "nrql_condition": workflow["nrql_condition"],
                        "attribute.accumulations.policyName": workflow[
                            "attribute.accumulations.policyName"
                        ],
                        "attribute.labels.policyIds": workflow[
                            "attribute.labels.policyIds"
                        ],
                        "policy.operator": workflow["policy.operator"],
                        "policy.values": workflow["policy.values"],
                        "channel_id": channel_id,
                        "destination_channel_name": None,
                        "destination_channel_type": None,
                        "destination_id": None,
                        "destination_key": None,
                        "destination_value": None,
                    }
                )

    return mapped_data


def generate_workflows_with_channels():
    # Load workflows_with_alert_policies data
    with open("workflows_with_alert_policies.csv", mode="r", encoding="utf-8") as file:
        workflows_data = list(csv.DictReader(file))

    # Load channels_and_destinations data
    with open("channels_and_destinations.csv", mode="r", encoding="utf-8") as file:
        channels_data = list(csv.DictReader(file))

    print("Mapping workflows with channels...")
    mapped_data = map_workflows_with_channels(workflows_data, channels_data)
    print(f"Mapped {len(mapped_data)} rows.")

    print("Writing workflows_with_channels.csv...")
    write_to_csv(mapped_data, "workflows_with_channels.csv")
    print("Data written to 'workflows_with_channels.csv'.")


def main():
    # 1st part
    generate_workflows_with_alert_policies()
    generate_channels_and_destinations()

    # 2nd part
    generate_workflows_with_channels()


if __name__ == "__main__":
    main()
