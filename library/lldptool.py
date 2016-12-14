#!/usr/bin/python


DOCUMENTATION = '''
---
module: vsd_monit
short_description: Verify the summary of vsd processes via monit
options:
  name:
    description:
      - The name of the I(monit) program/process
    required: true
    default: null
  state:
    description:
      - The state of service
    required: true
    default: null
    choices: [ "summary" ]
'''

EXAMPLES = '''
# Verify the state of program "ntpd-status" state.
- lldptool: port=eth0
'''

import datetime
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.six import b

def main():
    arg_spec = dict(
        port=dict(required=True)
    )

    module = AnsibleModule(argument_spec=arg_spec)

    port = module.params['port']

    LLDPTOOL = module.get_bin_path('lldptool', True)

    startd = datetime.datetime.now()

    cmd = "%s -t -n -i %s" % (LLDPTOOL, port)
    rc, out, err = module.run_command(cmd, check_rc=True)

    endd = datetime.datetime.now()

    delta = endd - startd

    if err is None:
        err = b('')

    if out is None:
        out = b('')

    if 2 > len(out.split('\n')):
        module.exit_json(cmd = cmd,
                         stdout = out,
                         stderr = err.strip(),
                         rawout = out,
                         rc = rc,
                         start = str(startd),
                         end = str(endd),
                         delta = str(delta),
                         changed=False)

    scratch = out.replace('End of LLDPDU TLV', '').replace('\n\t', '\t').strip()
    parsed = ""
    for line in scratch.split('\n'):
        my_list = line.split('\t')
        if 2 == len(my_list):
            my_other_list = my_list[1].split(': ')
            if 2 == len(my_other_list):
                parsed += "\"%s\": { \"%s\": \"%s\" }," % (my_list[0], my_other_list[0], my_other_list[1])
            else:
                parsed += "\"%s\": \"%s\"," % (my_list[0], my_list[1])
        else:
            sub=""
            if 2 == len(my_list[3].split(': ')):
                sub = my_list[3].split(': ')[1]
            parsed += "\"%s\": { \"%s\": \"%s\", \"%s\": \"%s\", \"%s\": \"%s\" }" % ( my_list[0],
                                                                                     my_list[1].split(': ')[0],
                                                                                     my_list[1].split(': ')[1],
                                                                                     my_list[2].split(': ')[0],
                                                                                     my_list[2].split(': ')[1],
                                                                                     my_list[3].split(': ')[0],
                                                                                     sub )
    parsed = "{ %s }" % parsed
        
    module.exit_json(cmd = cmd,
                     stdout = parsed,
                     stderr = err.strip(),
                     rawout = out,
                     rc = rc,
                     start = str(startd),
                     end = str(endd),
                     delta = str(delta),
                     changed=True)

if __name__ == '__main__':
    main()
