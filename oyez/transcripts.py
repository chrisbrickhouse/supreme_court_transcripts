import datetime
import os
import json
import textgrid
# TO DO:
#  [] Function to download audio, but not all at once for performance reasons

class OyezTranscript():
    def __init__(self, json_obj,fname='OyezTranscript'):
        if not json_obj['transcript']:
            raise ValueError('No transcript for this case.')
        if json_obj['damaged']:
            self.damaged = False
        else:
            self.damaged = True
        if json_obj['unavailable']:
            self.unavailable = False
        else:
            self.unavailable = True

        self.fname = fname.split('.json')[0]

        self.name = json_obj['transcript']['title']
        self._title = json_obj['title']
        self.type, date = self._title.split(' - ')
        self.date = datetime.datetime.strptime(date, '%B %d, %Y')
        
        self.media_links = json_obj['media_file']
        
        self._transcript_object = json_obj['transcript']
        self._parse_transcript(json_obj['transcript'])
        self.make_textgrid()

    def _parse_transcript(self, trans_obj):
        # I think I want an array of turns
        #  each turn is a dict with start, stop, speaker, text
        turns = []
        for section in trans_obj['sections']:
            for turn in section['turns']:
                try:
                    speaker = turn['speaker']['identifier']
                    lname = turn['speaker']['last_name']
                except TypeError:
                    speaker = 'Unknown'
                    lname = 'Unknown'
                for phrase in turn['text_blocks']:
                    tmp = Turn()
                    tmp.add(phrase, speaker, lname)
                    turns.append(tmp)
        self.turns = turns

    def make_textgrid(self):
        turns = self.turns
        start = turns[0]['start']
        stop = turns[-1]['stop']
        self.tg = textgrid.TextGrid(minTime=start, maxTime=stop)
        spkr_to_tier = {}
        for turn in turns:
            if turn['speaker'] not in spkr_to_tier:
                spkr_to_tier[turn['speaker']] = textgrid.IntervalTier(name=turn['last_name'],minTime=start,maxTime=stop)
            spkr_to_tier[turn['speaker']].add(turn['start'],turn['stop'],turn['text'])
        for tier in spkr_to_tier.values():
            self.tg.append(tier)
        with open(self.fname+'.textgrid', 'w') as f:
            self.tg.write(f)

class Turn(dict):
    def __init__(self,*args, **kwargs):
        super(Turn, self).__init__(self,*args,**kwargs)

    def add(self, phrase_obj, speaker, lname):
        super(Turn, self).__setitem__('speaker',speaker)
        super(Turn, self).__setitem__('last_name', lname)
        super(Turn, self).__setitem__('start', phrase_obj['start'])
        super(Turn, self).__setitem__('stop', phrase_obj['stop'])
        super(Turn, self).__setitem__('text', phrase_obj['text'])

def main():
    # The following is identical to stuff in corpus.py, should be combined
    file_list = os.listdir('./oyez/cases')
    transcribed = [x for x in file_list if "-t" in x]
    # end refactor block
    cases_transcribed = {}
    for transcript in transcribed:
        if '08-472' not in transcript:
            continue
        with open('./oyez/cases/'+transcript, 'r') as f:
            trans_obj = json.load(f)
        try:
            trans_inst = OyezTranscript(trans_obj,fname=transcript)
        except ValueError:
            print(f"Warning: Could not create transcript instance for {transcript}.")
            continue
        case_name = trans_inst.name
        if case_name not in cases_transcribed:
            cases_transcribed[case_name] = []
        cases_transcribed[case_name].append(trans_inst)
        print('Success')
    return cases_transcribed
