# topology-collector

A repository for code that collects the following information about interfaces on compute hosts:

1. Neighbor LLDP connectivity information
2. VF port PCI information for the interface

The output of the code is a JSON report.

## Summary instructions

1. Clone the repo to the OpenStack controller node (requires git)
2. Install Ansible 2.1+ on the OpenStack Controller node
3. Configure passwordless ssh from the OpenStack Conroller node to all compute nodes
4. Update local variables (see below)
5. Execute `ansible-playbook -i controller_hosts get_computes.yml` (Skip if you hand-edit `compute_hosts` or you have already run this step previously and no changes in the list of compute nodes are required.)
6. Execute `ansible-playbook -i compute_hosts get_topo.yml`

## Details

### Assumptions
1. The interfaces to be processed on the compute nodes are currently `UP` as reported by the command `ip addr`
2. The VFs for the interfaces to be processed on the compute nodes are listed in the directory /sys/class/net/<interface>/device/virt* on each compute node

### Input variables

Input variables are contained in the following files:
1. `user_vars.yml`
2. `controller_hosts`
3. `compute_hosts`

#### `user_vars.yml`

- `temp_dir`, the location on the OpenStack controller node where intermediate files are written to and read from
- `output_dir`, the location on the OpenStack controller node where the date-stamped output files will be written
- `output_file_prefix`, text to prepend to the output file name, e.g. <output_file_prefix>.<date>@<time>.json.
- `interface_regex`, regex to match interface names on the compute nodes. Default is `['*']`

#### `controller_hosts`

Contains a flat list of controller node host names or IP addresses under the tag `[controllers]`. In most cases, this will be a list of one and only one controller.

#### `compute_hosts`

Contains a flat list of compute node host names or IP addresses under the tag `[computes]`. This list may be populated manually or automatically. Automatic population is achieved using the get-computes role.

### `get-computes`

The `get-computes` role queries the OpenStack controller node for the list of nova hypervisors. It parses the output and writes the result to `./compute_hosts`.

The `get-computes` role is 

### `collect_topo.yml`

The `collect_topo.yml` playbook is nothing more that a set of includes of other playbooks. These component playbooks may be executed individually. The other playbooks, each representing an Ansible role, are:

- `clean_tmp.yml`, when executed, this playbook destroys the `temp_dir` on disk. This is done to prevcent old files from polluting a current run.
- `topology.yml`, when executed, queries each hosts listed in the `hosts` file's `computes` group. The output of this stage is a set of files, one per compute node, in the `temp_dir`.
- `report.yml`, when executed, pulls in the content of each JSON file found in `temp_dir` and creates a full report for all compute nodes. The full report is written to `output_dir` using a unique file name.

### Custom Ansible Modules

The implementation includes the following custom Ansible modules written in Python:

- `library\interfaces.py`, a module to query each compute node for information about its interfaces. Matching interfaces are filtered using `state` and regex match on name.
- `library\topology.py`, a module that executes the commands for collecting infomration about each interface, converting the output to JSON.

### Output

The output of the run will be a file that contains a JSON string. The schema itself and a sample output can be found in the `schema` subdirectory and pasted, below.

The name of the file will be of the form `<output_file_prefix>.<date>@<time>.json`. For example, `blue.2016-11-21@14:16:18.json`.

#### JSON schema

```
{
    "$schema": "http://json-schema.org/draft-04/schema#",
    "title": "Nuage Topology Collector Report",
    "description": "A report of 1) the mapping between compute host interfaces and VSG ToR ports and 2) the VF PCI information for the interfaces",
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
                "hypervisor hostname": {
                    "type": "string",
                    "description": "Hypervisor hostname of the compute host"
                },
                "service_host name": {
                    "type": "string",
                    "description": "service_host name of the compute host"
                },
                "interfaces": {
                    "type": "array",
                    "description": "zero or more interfaces on the compute host",
                    "items": {
                        "$ref": "#/definitions/interface"
                    }
                }
            },
            "required": [ "hypervisor hostname", "service_host name",  "interfaces" ]
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

#### JSON sample

```
{
    "datetime": "2016-12-17@04:06:05",
    "compute-hosts": [
        {
            "hypervisor hostname": "andc-ubuntu02.an.nuagenetworks.net",
            "service_host name": "andc-ubuntu02",
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
