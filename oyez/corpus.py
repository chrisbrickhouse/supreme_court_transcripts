import json
import os
from fnmatch import fnmatch
from datetime import datetime

class Case():
    def __init__(self, docket_info, corpus):
        self._corpus = corpus
        self.irregular = False
        self.fname_root = docket_info
        self._year, self.docket = docket_info.split('.')
        if '_' in self._year:
            # This happens sometimes with like 1940_1955 and idky
            self.irregular = True
            return
        if 'orig' in self.docket:
            # Original jurisdication cases have different docket structure
            # the number is not the term, but the docket number, and it uses a
            # space to separate the "ORIG" from the docket number rather than
            # the hyphen seen in appelate cases.
            self.orig=True
            self.term = self._year
            self.docket_number = self.docket.upper().replace('_',' ')
        else:
            self.orig=False
            self.term, self.docket_number = self.docket.split('-')

    @property
    def year(self):
        return int(self._year)
    
    def load_summary(self, json_obj):
        self._summary = json_obj
        cite_o = json_obj['citation']
        self.volume = cite_o['volume']
        self.page = cite_o['page']
        self.oyez_id = json_obj['ID']
        self.name = json_obj['name']
        self.questions = json_obj['question']
        self.description = json_obj['description']
        self.justia_url = json_obj['justia_url']
        timeline_o = json_obj['timeline']
        self.timeline = []
        for event_o in timeline_o:
            self.timeline.append(Event(event_o))

    def load_votes(self, case_obj):
        if case_obj['ID'] != self.oyez_id:
            print(f"Error:Vote file ID {case_obj['ID']} does not match summary ID {self.oyez_id}.\n Marking irregular and aborting vote loading.")
            self.irregular = True
            return
        #self.first_party = Party(case_obj)
        #self.second_party = Party(case_obj)
        self.advocates = []
        if not case_obj['advocates']:
            print(f"Warning: No advocates in case {self.docket}? Marking irregular and aborting vote loading.")
            self.irregular = True
            return
        for adv_o in case_obj['advocates']:
            try:
                person = self._make_advocate(adv_o)
            except:
                print(f"Could not make an advocate for {self.docket}. Dumping advocate block:\n{case_obj['advocates']}")
                continue
            person.add_case(case_obj, adv_o, 'advocate')
            self.advocates.append(person)
        self.decisions = []
        self.justices = []
        if not case_obj['decisions']:
            print(f"Warning: No decisions for {case_obj['docket_number']}. Marking irregular and aborting vote loading.")
            self.irregular = True
            return
        for dec_o in case_obj['decisions']:
            decision = {
                    'held': dec_o['description'],
                    'majority_tally': dec_o['majority_vote'],
                    'minority_tally': dec_o['minority_vote'],
                    'winning_party': dec_o['winning_party'],
                    'votes': {}
                }
            if not dec_o['votes']:
                print(f"Warning: No votes for {case_obj['docket_number']}. Marking irregular and aborting vote loading.")
                self.irregular = True
                return
            for justice_o in dec_o['votes']:
                #if justice_o['vote'] == "none":
                #    continue
                #try:
                person = self._make_justice(justice_o['member'])
                #except:
                #    print(f"Could not make a justice for {self.docket}. Dumping vote block:\n{justice_o}")
                #    continue
                #    pass
                vote = {
                        'ideology': justice_o['ideology'],
                        'seniority': justice_o['seniority'],
                        'sided_with': justice_o['vote']
                    }
                person.add_case(case_obj,justice_o,'justice')
                self.justices.append(person)
                decision['votes'][justice_o['member']['identifier']] = vote
            self.decisions.append(decision)

    def _make_advocate(self, adv_o):
        adv_id = adv_o['advocate']['identifier']
        if adv_id in self._corpus.people:
            a = self._corpus.people[adv_id]
            a.add_role('justice', justice_o)
            return a
        adv_name = adv_o['advocate']['name']
        adv_oyez_id = adv_o['advocate']['ID']
        adv = Person(adv_id, adv_name, adv_oyez_id)
        adv.add_role('advocate', adv_o)
        self._corpus.people[adv_id] = adv
        return adv

    def _make_justice(self, justice_o):
        j_id = justice_o['identifier']
        if j_id in self._corpus.people:
            j = self._corpus.people[j_id]
            j.add_role('justice', justice_o)
            return j
        j_name = justice_o['name']
        j_oyez_id = justice_o['ID']
        justice = Person(j_id, j_name, j_oyez_id)
        justice.add_role('justice', justice_o)
        self._corpus.people[j_id] = justice
        return justice

    def load_transcript(self):
        # Find files then load json, probably worth parsing later
        pass

class Party():
    def __init__(self):
        pass

class Person():
    def __init__(self, identifier, name, oyez_id):
        self.identifier = identifier
        self.name = name
        self.oyez_id = oyez_id
        self.roles = {}
        self.appeared_in = []

    def add_role(self, role, role_object):
        print(role)
        if role in self.roles:
            return
        if role == 'advocate':
            self.roles[role] = Advocate(self, role_object)
        elif role == 'justice':
            self.roles[role] = Justice(self, role_object)
        else:
            raise ValueError(f"Unknown role {role}")

    def add_case(self, case_obj, appearance_obj, role):
        self.appeared_in.append(case_obj['docket_number'])
        self.roles[role].add_appearance(case_obj, appearance_obj)

class Role():
    def __init__(self, person_inst, role_obj):
        #self._object = role_obj  # DO NOT USE! Is only role for case that created it!
        self._person = person_inst
        self.appearances = {}

    def add_appearance(self, docket, data):
        self.appearances[docket] = data

class Advocate(Role):
    def __init__(self, *args, **kwargs):
        super(Advocate, self).__init__(*args, **kwargs)
    
    def add_appearance(self, case_obj, appearance_obj):
        docket = case_obj['docket_number'] 
        data = {
                'description': appearance_obj['advocate_description'],
                'case_name': case_obj['name']
            }
        super(Advocate,self).add_appearance(docket, data)

class Justice(Role):
    def __init__(self, *args, **kwargs):
        super(Justice, self).__init__(*args, **kwargs)
        print(args)
        if len(args[1]['roles']) > 1:
            print(f"Warning: More than one role for {self._person.name}. Using first role {args[1]['roles'][0]['role_title']}.")
        self.appointed_by = args[1]['roles'][0]['appointing_president']
    
    def add_appearance(self, case_obj, appearance_obj):
        docket = case_obj['docket_number'] 
        r0 = appearance_obj['member']['roles'][0]
        if len(appearance_obj['member']['roles']) > 1:
            print(f"Warning: More than one role for {self._person.name}. Using first role {r0['role_title']}.")
        data = {
                'description': r0['role_title'],
                'case_name': case_obj['name']
            }
        super(Justice,self).add_appearance(docket, data)

class Event():
    def __init__(self, event_obj):
        self.type = event_obj['event']
        self.dates = [ datetime.fromtimestamp(x) for x in event_obj['dates'] ]

class Roladex(dict):
    def __init__(self, *args, **kwargs):
        super(Roladex, self).__init__(*args,**kwargs)

class CaseCorpus(dict):
    def __init__(self, *args, **kwargs):
        super(CaseCorpus, self).__init__(*args,**kwargs)
        self._dockets_to_key = {}
        self.summary_json = kwargs['json_obj']
        self.people = Roladex()

    def __setitem__(self, key, value):
        super(CaseCorpus, self).__setitem__(key, value)
        if value.docket not in self._dockets_to_key:
            self._dockets_to_key[value.docket] = []
        self._dockets_to_key[value.docket].append(key)

    def build(self, name_list, start=1000, end=3000):
        case_summaries = self.summary_json
        for case_name in name_list:
            try:
                case_inst = Case(case_name, self)
            except:
                print(f"Warning: Could not build case instance for {case_name}")
                continue
            if case_inst.irregular or case_inst.orig:
                continue
            if case_inst.year < start or case_inst.year > end:
                continue
            summary = [entry for entry in case_summaries if entry['docket_number'] == case_inst.docket]
            if len(summary) == 0:
                print(f"Warning: No entry found for {case_name}")
                continue
            case_inst.load_summary(summary[0])
            self.__setitem__(case_name,case_inst)

    def build_votes(self, file_list, prefix='./oyez/cases/'):
        for fname in file_list:
            if '-t' in fname:
                # Don't care about transcripts right now
                continue
            elif '_' in fname:
                # Filters ORIG and those weird YEAR_YEAR files
                continue
            year, docket, ext = fname.split('.')
            if ext != 'json':
                print(f"Warning: Unknown file type. Skipping {fname}")
            if '-' not in docket:
                # It's an old case that I don't feel like handling right now
                continue
            with open( prefix+fname, 'r') as f:
                json_obj = json.load(f)
            case_inst = self.search_by_docket(docket)
            if type(case_inst) is list:
                print(f"Error: {docket} did not produce unique result. Dumping results:\n{case_inst}")
                continue
            case_inst.load_votes(json_obj)

    def search_by_docket(self, docket):
        """Search the corpus by docket number.

        If there is a unique entry, it returns the object
        otherwise it returns a list of matches (or an empty list if no matches)

        Returns: Case or list
        """
        try:
            key_list = self._dockets_to_key[docket]
        except KeyError:
            return []
        if len(key_list) == 1:
            return self.__getitem__(key_list[0])
        else:
            return [self.__getitem__(k) for k in key_list]

def read_summary():
    with open('./oyez/case_summaries.json','r') as f:
        case_summaries = json.load(f)
    return case_summaries

def build():
    case_summaries = [x for x in read_summary() if x['citation'] != None ]
    
    cases = CaseCorpus(json_obj=case_summaries)
    
    file_list = os.listdir('./oyez/cases')
    # Cases with oral arg transcripts have -t\d\d appended
    transcribed = [x for x in file_list if "-t" in x]
    names = list(set([x.split('-t')[0] for x in transcribed]))
    names.sort()  # Sort by year before iterating
    
    cases.build(names,1000,3000)
    cases.build_votes(file_list)
    
    return cases
