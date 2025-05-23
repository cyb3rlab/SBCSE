"""
This module is used to generate Maude code.

maude_class_monitor(PID:str, ocom_statuses=None) is a decorator that is used to monitor the class to collect data.
Different classes could have same PID.
ocom_statuses is a list of the member variables that need to be monitored.

maude_fnuc_monitor(func) is a decorator that is used to monitor the function to collect data.

generator_maude_code() is the function that generates the Maude code.
"""
from formal_verification.utils.data_model import MaudemodGenerator

class Maude_Generator():
    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.trans = []
            self.tran_op_set = set()
            self.pid_set = set()
            self.cmd_set = set()
            self.ocom_statuses = {}
            self._initialized = True
            self.config_dict = {}
            self.ic_list = []

    def find_trans(self):
        contents = self.trans
        ocom_name = None
        tran_name = None
        rltr_name = 0
        nw = None
        idx = 0
        temp_tran_dict = {}
        tran_lst = []
        idx_lst = []

        while(contents != []):
            content = contents[idx]
            for key, value in content.items():
                if key == 'tran_name' and tran_name is None and (ocom_name is None or ocom_name==value.split('.')[0]):
                    ocom_name = value.split('.')[0]
                    tran_name = value
                    nw = None
                    idx_lst.insert(0, idx)
                    idx += 1
                elif key.endswith('recvcmd') and tran_name is None and (ocom_name is None or ocom_name==value.split('.')[0]):
                    ocom_name = key.split('.')[0]
                    tran_name = key
                    for tran_values in tran_lst[-1].values():
                        tran_values[-1]['nw']['end'] = value['end']
                    new_value = {'start': value['end'], 'end': 'None'}
                    nw = {'nw': new_value}
                    idx_lst.insert(0, idx)
                    idx += 1
                elif ocom_name is None:
                    ocom_name = key.split('.')[0]
                    idx_lst.insert(0, idx)
                    temp_tran_dict.update({key: value})
                    idx += 1
                elif key == 'tran_name' and ocom_name == value.split('.')[0]:
                    if len(temp_tran_dict) == 0:
                        for i in idx_lst:
                            contents.pop(i)
                        idx_lst = []
                        idx = 0
                        tran_name = None
                        ocom_name = None
                        continue
                    for i in idx_lst:
                        contents.pop(i)

                    for o_name, o_value in self.config_dict.items():
                        if o_name.split('.')[0] == ocom_name:
                            if o_name in temp_tran_dict:
                                self.config_dict[o_name] = temp_tran_dict[o_name]['end']
                            else:
                                temp_tran_dict.update({o_name: {'start': o_value, 'end': o_value}})

                    temp_tran_dict.update(nw)
                    tran_lst.append({f'tran{rltr_name}': [{k: v} for k, v in temp_tran_dict.items()]})
                    self.tran_op_set.add(f'tran{rltr_name}')
                    rltr_name += 1
                    temp_tran_dict = {}
                    idx_lst = []
                    idx = 0
                    tran_name = None
                    ocom_name = None
                    continue
                elif key.endswith('recvcmd') and ocom_name == key.split('.')[0]:
                    if len(temp_tran_dict) == 0:
                        for i in idx_lst:
                            contents.pop(i)
                        idx_lst = []
                        idx = 0
                        tran_name = None
                        ocom_name = None
                        continue
                    for i in idx_lst:
                        contents.pop(i)

                    for o_name, o_value in self.config_dict.items():
                        if o_name.split('.')[0] == ocom_name:
                            if o_name in temp_tran_dict:
                                self.config_dict[o_name] = temp_tran_dict[o_name]['end']
                            else:
                                temp_tran_dict.update({o_name: {'start': o_value, 'end': o_value}})
                    
                    temp_tran_dict.update(nw)
                    tran_lst.append({f'tran{rltr_name}': [{k: v} for k, v in temp_tran_dict.items()]})
                    self.tran_op_set.add(f'tran{rltr_name}')
                    rltr_name += 1
                    temp_tran_dict = {}
                    idx_lst = []
                    idx = 0
                    tran_name = None
                    ocom_name = None
                    continue
                elif ocom_name == key.split('.')[0]:
                    idx_lst.insert(0, idx)
                    temp_tran_dict.update({key: value})
                    idx += 1
                elif key.endswith('recvcmd'):
                    new_value = {'start': 'None', 'end': value['start']}
                    nw = {'nw': new_value}
                    idx += 1
                else:
                    idx += 1
                if idx == len(contents):
                    if len(temp_tran_dict) == 0:
                        for i in idx_lst:
                            contents.pop(i)
                        idx_lst = []
                        idx = 0
                        tran_name = None
                        ocom_name = None
                        continue
                    for i in idx_lst:
                        contents.pop(i)

                    for o_name, o_value in self.config_dict.items():
                        if o_name.split('.')[0] == ocom_name:
                            if o_name in temp_tran_dict:
                                self.config_dict[o_name] = temp_tran_dict[o_name]['end']
                            else:
                                temp_tran_dict.update({o_name: {'start': o_value, 'end': o_value}})

                    temp_tran_dict.update(nw)
                    tran_lst.append({f'tran{rltr_name}': [{k: v} for k, v in temp_tran_dict.items()]})
                    self.tran_op_set.add(f'tran{rltr_name}')
                    rltr_name += 1
                    temp_tran_dict = {}
                    idx_lst = []
                    idx = 0
                    tran_name = None
                    ocom_name = None
                    continue
        return tran_lst 

    def generator_maude_code(self):
        output = ''
        cmdprs = []
        ocomprs = []
        ic_list = []

        with open('./formal_verification/src/utils.maude', 'r') as f:
            content = f.read()
            output += content
            output += '\n\n'
        

        for fmod_name in self.ocom_statuses.keys():
            if fmod_name.endswith('cmd'):
                cmdprs.append(fmod_name)
            else:
                ocomprs.append(fmod_name)

                value  = getattr(self, f'_ini_{fmod_name}')
                if isinstance(value, str):
                    self.config_dict.update({fmod_name: value+f".{fmod_name}"})
                    ic_list.append("("+fmod_name+": " + value+f".{fmod_name}"+")")
                else:
                    self.config_dict.update({fmod_name: str(value)})
                    ic_list.append("("+fmod_name+": " + str(value) +")")

            fmod_sort = fmod_name.capitalize()
            output += MaudemodGenerator().status(fmod_name, fmod_sort, list(self.ocom_statuses[fmod_name]))
            output += '\n\n'
        
        trans = self.find_trans()

        output += MaudemodGenerator().pid(list(self.pid_set))
        output += '\n\n'
            
        output += MaudemodGenerator().message(cmdprs)
        output += '\n\n'

        with open('./formal_verification/src/MQTT.maude', 'r') as f:
            content = f.read()
            output += content
            output += '\n\n'

        output += MaudemodGenerator().tran(list(self.tran_op_set))
        output += '\n\n'
        output += MaudemodGenerator().ocom(ocomprs)
        output += '\n\n'

        with open('./formal_verification/src/config.maude', 'r') as f:
            content = f.read()
            output += content
            output += '\n\n'
        
        output += MaudemodGenerator().init_config(ic_list)
        output += '\n\n'

        output += MaudemodGenerator().protocol(trans)
        output += '\n\n'

        output += MaudemodGenerator().formula()
        output += '\n\n'

        with open('./formal_verification/fv.maude', 'w') as f:
            f.write(output)

def maude_class_monitor(PID:str, ocom_statuses=None):
    def maudemodelstatusgenerator(cls):
        cls.PID = PID
        Maude_Generator().pid_set.add(PID)

        for ocom_status in ocom_statuses:
            Maude_Generator().ocom_statuses.update({f"{PID}.{ocom_status.replace('_', '')}": set()}) 

        Maude_Generator().ocom_statuses.update({f"{PID}.sendcmd": set()}) 

        original_init = cls.__init__
        def new_init(self, *args, **kwargs):
            original_init(self, *args, **kwargs)
        cls.__init__ = new_init
        
        for ocom_status in ocom_statuses:
            def getter(self, attr=ocom_status):
                return getattr(self, f'_{attr}', None)
            
            def setter(self, value, attr=ocom_status):
                maude_attr = attr.replace('_', '')

                if isinstance(value, str):
                    Maude_Generator().ocom_statuses[f"{self.PID}.{maude_attr}"].add(value.replace('_', '')+f'.{self.PID}.{maude_attr}')
                value_old = getattr(self, f'_{attr}', None)
                if value_old == None and isinstance(value, str):
                    setattr(Maude_Generator(), f'_ini_{self.PID}.{maude_attr}', value)
                    if attr.endswith('cmd'):
                        Maude_Generator().trans.append({f'{self.PID}.{maude_attr}':{'start': f'{value_old}', 'end': f'{value}.{self.PID}.{maude_attr}'}})
                elif isinstance(value, str):
                    Maude_Generator().trans.append({f'{self.PID}.{maude_attr}':{'start': f'{value_old}.{self.PID}.{maude_attr}', 'end': f'{value}.{self.PID}.{maude_attr}'.replace('_','')}})
                    pass
                elif value_old == None and not isinstance(value, str) :
                    setattr(Maude_Generator(), f'_ini_{self.PID}.{maude_attr}', value)
                else:
                    Maude_Generator().trans.append({f'{self.PID}.{maude_attr}':{'start': f'{value_old}', 'end': f'{value}'}})

                if not value is None and isinstance(value, str):
                    setattr(self, f'_{attr}', value.replace('_', ''))
                else:
                    setattr(self, f'_{attr}', value)

            setattr(cls, ocom_status, property(fget=getter, fset=setter))
        return cls
    return maudemodelstatusgenerator

def maude_fnuc_monitor(func):
    def maudetrangenerator(self, *args, **kwargs):
        tran_name = func.__name__.replace('_', '') + \
                    ''.join(str(arg).replace('_', '') for arg in args[:2]) + \
                    ''.join(f"{value}" for value in kwargs.values())
        call_info = {
            'tran_name': f'{self.PID}.{tran_name}',
        }
        Maude_Generator().ocom_statuses[f'{self.PID}.sendcmd'].add(tran_name+f'.{self.PID}.{tran_name}')
        Maude_Generator().trans.append(call_info)
        return func(self, *args, **kwargs)
    return maudetrangenerator