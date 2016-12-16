# lldpcollector

A repository for code to collect LLDP neighbor TLVs from 1 or more nodes and produce a JSON report.

## Prerequisites
1. Ansible 2.1+ installed on node where the playbook will run
2. Network connectivity from the Ansible host to each compute node
3. Passwordless ssh configured from the Ansible host to each compute node

## Input variables

1. List of compute host names or IP addresses
2. Path to directory to write report to

## Invocation

`ansible-playbook -i hosts collect.yml`

## Output

The output of the run will be a file that contains a JSON string. The schema itself and a sample output can be found in the `schema` subdirectory and pasted, below.

The name of the file will be of the form `collector.<date-time>.json`. For example, `collector.2016-11-21@14:16:18.json`.

### JSON schema

```
{
    "$schema": "http://json-schema.org/draft-04/schema#",
    "title": "Nuage LLDP Port mapping",
    "description": "A report of the port mapping between a collection of compute hosts and NSG TOR devices",
    "type": "object",
    "properties": {
        "datetime": {
            "description": "The date and time this report was generated",
            "type": "string"
        },
        "compute-hosts": {
            "type": "array",
            "items": {
                "$ref": "#/definitions/compute-host"
            }
        }
    },
    "required": ["datetime", "compute-hosts"],
    "definitions": {
        "compute-host": {
            "properties": {
                "name": {
                    "type": "string",
                    "description": "System name of the compute host"
                },
                "interfaces": {
                    "type": "array",
                    "description": "zero or more interfaces on the compute host",
                    "items": {
                        "$ref": "#/definitions/interface"
                    }
                }
            },
            "required": [ "name", "interfaces" ]
        },
        "interface": {
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The name of the interface"
                },
                "bus-info": {
                    "type": "string",
                    "description": "The PCI bus information for the interface"
                },
                "neighbor-system-name": {
                    "type": "string",
                    "description": "The system name of the connected neighbor"
                },
                "neighbor-system-port": {
                    "type": "string",
                    "description": "The port designation on the connected neighbor"
                }
            },
            "required": [ "name", "bus-info", "neighbor-system-name", "neighbor-system-port" ]
        }
    }
}
```

### JSON sample

```
{
  "datetime": "2016-11-21@14:16:18",
  "compute-hosts": [
      {
        "name": "cas-cs3-022",
        "interfaces": [
          {
            "name": "ens15f0",
            "bus-info": "0000:03:00.0",
            "neighbor-system-name": "cas-sf3-009",
            "neighbor-system-port": "1/1/1"
          },
          {
            "name": "ens15f1",
            "bus-info": "0000:03:00.1",
            "neighbor-system-name": "cas-sf3-009",
            "neighbor-system-port": "1/2/1"
          }
        ]
      },
      {
        "name": "cas-cs3-023",
        "interfaces": [
          {
            "name": "ens15f0",
            "bus-info": "0000:03:00.0",
            "neighbor-system-name": "cas-sf3-009",
            "neighbor-system-port": "1/3/1"
          },
          {
            "name": "ens15f1",
            "bus-info": "0000:03:00.1",
            "neighbor-system-name": "cas-sf3-009",
            "neighbor-system-port": "1/4/1"
          }
        ]
      }
    ]
}
```
