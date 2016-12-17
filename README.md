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
    "description": "A report of the port mapping between a collection of compute hosts and VSG ToR devices",
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
                "vf-info": {
                    "type": "array",
                    "description": "The VF information for the interface",
                    "items": {
                        "$ref": "#/definitions/vf-info"
                    }
                },
                "neighbor-system-name": {
                    "type": "string",
                    "description": "The system name of the connected neighbor"
                },
                "neighbor-system-mgmt-ip": {
                    "type": "string",
                    "description": "The management IP address of the connected neighbor"
                },
                "neighbor-system-port": {
                    "type": "string",
                    "description": "The port designation on the connected neighbor"
                }
            },
            "required": [ "name", "neighbor-system-name", "neighbor-system-port" ]
        },
        "vf-info": {
            "properties": {
                "pci-id": {
                    "type": "string",
                    "description": "The VF PCI ID"
                },
                "device-name": {
                    "type": "string",
                    "description": "The VF device name"
                }
            }
        }
    }
}
```

### JSON sample

```
{
    "datetime": "2016-12-17@04:06:05",
    "compute-hosts": [
        {
            "name": "10.31.178.22",
            "interfaces": [

                {
 "name": "eno1",
 "vf_info": [],
 "neighbor-system-name": "cas-sf3-009",
 "neighbor-system-mgmt-ip": "10.101.2.2",
 "neighbor-system-port": "1/1/9"  },

                {
 "name": "eno4",
 "vf_info": [],
 "neighbor-system-name": "None",
 "neighbor-system-mgmt-ip": "None",
 "neighbor-system-port": "None"  },

                {
 "name": "ens15f0",
 "vf_info": [],
 "neighbor-system-name": "cas-sf3-009",
 "neighbor-system-mgmt-ip": "10.101.2.2",
 "neighbor-system-port": "1/1/1"  },

                {
 "name": "ens15f1",
 "vf_info": [
 { "device-name": "virtfn0", "pci-id": "0000:03:06.0" },
 { "device-name": "virtfn1", "pci-id": "0000:03:06.1" },
 { "device-name": "virtfn10", "pci-id": "0000:03:07.2" },
 { "device-name": "virtfn11", "pci-id": "0000:03:07.3" },
 { "device-name": "virtfn12", "pci-id": "0000:03:07.4" },
 { "device-name": "virtfn13", "pci-id": "0000:03:07.5" },
 { "device-name": "virtfn14", "pci-id": "0000:03:07.6" },
 { "device-name": "virtfn15", "pci-id": "0000:03:07.7" },
 { "device-name": "virtfn16", "pci-id": "0000:03:08.0" },
 { "device-name": "virtfn17", "pci-id": "0000:03:08.1" },
 { "device-name": "virtfn18", "pci-id": "0000:03:08.2" },
 { "device-name": "virtfn19", "pci-id": "0000:03:08.3" },
 { "device-name": "virtfn2", "pci-id": "0000:03:06.2" },
 { "device-name": "virtfn20", "pci-id": "0000:03:08.4" },
 { "device-name": "virtfn21", "pci-id": "0000:03:08.5" },
 { "device-name": "virtfn22", "pci-id": "0000:03:08.6" },
 { "device-name": "virtfn23", "pci-id": "0000:03:08.7" },
 { "device-name": "virtfn24", "pci-id": "0000:03:09.0" },
 { "device-name": "virtfn25", "pci-id": "0000:03:09.1" },
 { "device-name": "virtfn26", "pci-id": "0000:03:09.2" },
 { "device-name": "virtfn27", "pci-id": "0000:03:09.3" },
 { "device-name": "virtfn28", "pci-id": "0000:03:09.4" },
 { "device-name": "virtfn29", "pci-id": "0000:03:09.5" },
 { "device-name": "virtfn3", "pci-id": "0000:03:06.3" },
 { "device-name": "virtfn30", "pci-id": "0000:03:09.6" },
 { "device-name": "virtfn31", "pci-id": "0000:03:09.7" },
 { "device-name": "virtfn4", "pci-id": "0000:03:06.4" },
 { "device-name": "virtfn5", "pci-id": "0000:03:06.5" },
 { "device-name": "virtfn6", "pci-id": "0000:03:06.6" },
 { "device-name": "virtfn7", "pci-id": "0000:03:06.7" },
 { "device-name": "virtfn8", "pci-id": "0000:03:07.0" },
 { "device-name": "virtfn9", "pci-id": "0000:03:07.1" }],
 "neighbor-system-name": "cas-sf3-009",
 "neighbor-system-mgmt-ip": "10.101.2.2",
 "neighbor-system-port": "1/2/1"  }
            ]
        }
    ]
}      
```
