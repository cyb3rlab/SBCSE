"""
This module contains the class MaudemodGenerator, which is used to provide data formats for generate Maude code.
"""
class MaudemodGenerator:
    def fmod_code(self, fmod_name, sort, ops_list, ctor=False):
        maude_code = "".join([
            f"fmod {fmod_name} is \n",
            f"\tsort {sort} . \n",
            f'\tops ',
            f" ".join(ops_list) + f" : -> {sort} [ctor]" if ctor else f" ".join(ops_list) + f" : -> {sort} ." ,
            "\nendfm"
            ])
        return maude_code

    def status(self, fmod_name, sort, ops_list, ctor=False):
        if len(ops_list) != 0:
            return self.fmod_code(fmod_name, sort, ops_list, ctor=ctor)
        else:
            maude_code = "".join([
            f"fmod {fmod_name} is \n",
            f"\tpr NZNAT .\n",
            f"\tsort {sort} . \n",
            f"\tsubsort NzNat < {sort} . \n",
            "\nendfm"
            ])
        return maude_code
    
    def pid(self, pid_list):
        maude_code = "".join([
            f"fmod PID is \n",
            f"\tsort Pid . \n",
            f'\tops ',
            f" ".join(pid_list) + f" : -> Pid [ctor] .",
            "\nendfm"
            ])
        return maude_code

    def mqtt_command(self, fmod_name, sort, ops_list):
        return self.fmod_code(fmod_name, sort, ops_list, ctor=True)
    
    def mqtt_topic(self, fmod_name, sort, ops_list):
        return self.fmod_code(fmod_name, sort, ops_list, ctor=True)

    def tran(self, tran_list):
        maude_code = "".join([
            f"fmod TRAN is \n",
            f"\tpr PID .\n",
            f"\tsort Tran . \n",
            f"\top notran : -> Tran [ctor] .\n"
            f''.join([f"\top {tr} : -> Tran [ctor] .\n" for tr in tran_list]),
            "\nendfm"
            ])
        return maude_code
        
    def message(self, cmds):
        maude_code = "".join([
            f"fmod MESSAGE is \n",
            f''.join([f"\tpr {cmd} .\n" for cmd in cmds]),
            f"\tsort Message . \n",
            f''.join([f"\top msg : {cmd.capitalize()} -> Message [ctor] .\n" for cmd in cmds]),
            "\nendfm"
            ])
        return maude_code
    
    def ocom(self, ocomlist):
        maude_code = "".join([
            f"fmod OCOM is \n",
            f"\tpr NETWORK .\n",
            f"\tpr PID .\n",
            f"\tpr TRAN .\n",
            f"\tpr NZNAT .\n",
            f''.join([f"\tpr {o} .\n" for o in ocomlist]),
            f"\tsort OCom . \n",
            f''.join([f"\top {o}:_  : {o.capitalize()} -> OCom .\n" for o in ocomlist]),
            f''.join(f"\top nw:_  : Network -> OCom .\n"),
            f''.join(f"\top tran:_  : Tran -> OCom .\n"),
            "\nendfm"
            ])
        return maude_code

    def init_config(self, ic_list):
        maude_code = "".join([
            f"fmod INIT-CONFIG is \n",
            f"\tpr CONFIG .\n",
            f"\top ic : -> Config .\n",
            f"\teq ic = ",
            f" ".join(ic_list),
            f" (nw: void)"
            f" (tran: notran)"
            f" .",
            "\nendfm"
            ])
        return maude_code
    
    def protocol(self, trans):
        maude_code = "".join([
            f"mod RCP is \n",
            f"\tpr CONFIG .\n",
            f"\tvar NW : Network .\n",
            f"\tvar T : Tran .\n\n",
            ])

        rl = None
        start_status_list = []
        end_status_list = []
        
        for tran in trans:
            rl = None
            start_status_list = []
            end_status_list = []
            for label, trs in tran.items():
                rl = label
                for ocom in trs:
                    for ocom_name, ocom_value in ocom.items():
                        if ocom_name == 'nw':
                            if ocom_value['start'] != 'None':
                                start_status_list.append(f'nw: '+'(msg('+ocom_value['start']+') NW)')
                            else:
                                start_status_list.append(f'nw: NW')
                            if ocom_value['end'] != 'None':
                                end_status_list.append(f'nw: '+'(msg('+ocom_value['end']+') NW)')
                            else:
                                end_status_list.append(f'nw: NW')
                        else:
                            start_status_list.append(ocom_name+": "+ocom_value['start'])
                            end_status_list.append(ocom_name+": "+ocom_value['end'])
                start_status_list.append('tran: T')
                end_status_list.append(f'tran: {rl}')
                maude_code += self.maude_rl(rl, start_status_list, end_status_list)
        maude_code += 'endm'
        return maude_code
    
    def maude_rl(self, label, start_status_list, end_status_list):
        rl_code = ''.join([
            f'\trl [{label}] :\n',
            f''.join(f'\t\t({status})\n' for status in start_status_list),
            f'\t\t=>',
            f''.join(f'\n\t\t({status})' for status in end_status_list),
            f' .\n\n',
        ])
        return rl_code
    
    def formula(self):
        formula_code = 'mod RCP-FORMULA is\n\tpr RCP .\n\tpr INIT-CONFIG .\nendm'
        return formula_code