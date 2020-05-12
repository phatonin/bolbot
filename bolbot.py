#!/bin/env python3.6

import os
import discord
import dotenv
import re
import perso
import regles

dotenv.load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')


class Parser:
    WS = re.compile(r'\s*')
    PATTERNS = (
        (
            re.compile(r'<@!(?P<userid>\d+)>', re.RegexFlag.IGNORECASE),
            'mention'
        ),
        (
            re.compile(r'(?P<dice_number>\d+)d(?P<dice_type>\d+)(?P<additional>[MB]*)', re.RegexFlag.IGNORECASE),
            'dice'
        ),
        (
            re.compile(r'(?P<dice_number>\d+)d(?P<additional>[MB]*)', re.RegexFlag.IGNORECASE),
            'dice'
        ),
        (
            re.compile(r'd(?P<dice_type>\d+)(?P<additional>[MB]*)', re.RegexFlag.IGNORECASE),
            'dice'
        ),
        (
            re.compile(r'(?P<number>[+-]?\d+)', re.RegexFlag.IGNORECASE),
            'number'
        ),
        (
            re.compile(r'(?P<sign>[+-])', re.RegexFlag.IGNORECASE),
            'sign'
        ),
        (
            re.compile(r'b(?:onus)', re.RegexFlag.IGNORECASE),
            'bonus'
        ),
        (
            re.compile(r'm(?:alus)', re.RegexFlag.IGNORECASE),
            'malus'
        ),
        (
            re.compile(r'\S+', re.RegexFlag.IGNORECASE),
            'junk'
        )
    )

    def __init__(self, client, userid):
        self.poubelle = []
        self.client = client
        self.persos = []
        self.mention(str(userid), userid)

    def ignorer(self, raw):
        self.poubelle.append(raw)
    
    def le_perso(self): # dernier
        for p, uid in reversed(self.persos):
            if p is not None:
                return p, uid
        for p, uid in reversed(self.persos):
            if uid is not None:
                return p, uid
        return None, None

    @staticmethod
    def _skip_ws(s, pos):
        m = Parser.WS.match(s, pos=pos)
        return pos + len(m.group())
        
    def parse(self, s):
        pos = 0
        while pos < len(s):
            pos = Parser._skip_ws(s, pos)
            for pat, meth in Parser.PATTERNS:
                m = pat.match(s, pos)
                if m is not None:
                    raw = m.group()
                    args = m.groupdict()
                    pos += len(raw)
                    getattr(self, '_' + meth)(raw, **args)
                    break
        return self.finish()
    
    def finish(self):
        raise NotImplementedError()
                
    def _mention(self, raw, userid):
        self.mention(raw, int(userid))
    
    def mention(self, raw, userid):
        if userid in self.client.pj_par_userid:
            p = self.client.pj_par_userid[userid]
        else:
            p = None
        self.persos.append((p, userid))
    
    def _dice(self, raw, dice_number=1, dice_type=6, additional=''):
        ladditional = additional.lower()
        self.dice(raw, int(dice_number), int(dice_type), ladditional.count('b'), ladditional.count('m'))
        
    def dice(self, raw, dice_number, dice_type, bonus, malus):
        self.ignorer(raw)
    
    def _number(self, raw, number):
        self.number(raw, int(number))
        
    def number(self, raw, number):
        self.ignorer(raw)
        
    def _sign(self, raw, sign):
        if sign == '+':
            self.sign(raw, 1)
        elif sign == '-':
            self.sign(raw, -1)
    
    def sign(self, raw, sign):
        self.ignorer(raw)
    
    def _bonus(self, raw):
        self.bonus(raw)
        
    def bonus(self, raw):
        self.ignorer(raw)
        
    def _malus(self, raw):
        self.malus(raw)
    
    def malus(self, raw):
        self.ignorer(raw)
    
    def _junk(self, raw):
        if raw.lower() in regles.Difficulte.MAP:
            self.difficulte(raw, regles.Difficulte.MAP[raw])
        elif raw.lower() in self.client.persos_par_nom:
            self.persos.append((self.client.persos_par_nom[raw.lower()], None))
        else:
            le_perso, _uid = self.le_perso()
            if le_perso is not None:
                if raw.lower() in le_perso.ref_map:
                    self.score(raw, le_perso.ref_map[raw])
                elif raw.lower() in le_perso.avantages.value:
                    self.bonus(raw)
                elif raw.lower() in le_perso.desavantages.value:
                    self.malus(raw)
                else:
                    self.junk(raw)
            else:
                self.junk(raw)

    def difficulte(self, raw, difficulte):
        self.ignorer(raw)
    
    def score(self, raw, ref):
        self.ignorer(raw)
    
    def junk(self, raw):
        self.ignorer(raw)

class Command:
    DIGITS = ('zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine')

    def __init__(self, client):
        self.client = client

    async def get_reply(self, message):
        raise NotImplementedError()
    
    def get_perso(self, message):
        result = []
        for t in message.content.lower().split():
            if t in self.client.persos_par_nom:
                result.append((None, self.client.persos_par_nom[t]))
        for user in message.mentions:
            if user.id in self.client.pj_par_userid:
                result.append((user, self.client.pj_par_userid[user.id]))
        if len(result) == 0 and message.author.id in self.client.pj_par_userid:
            result.append((message.author, self.client.pj_par_userid[message.author.id]))
        return result
    
    @staticmethod
    def perso_label(p, userid):
        if userid is None:
            return f'**{p.nom}**'
        if p is None:
            return f'<@!{userid}>'
        return f'**{p.nom}** (<@!{userid}>)'

    @staticmethod    
    def str_sign(n):
        if n == 1:
            return '+'
        if n == -1:
            return '-'

    @staticmethod    
    def dice_icons(dice):
        return ' '.join(f':{Command.DIGITS[n]}:' for n in dice)

class LanceJetParser(Parser):
    def __init__(self, client, userid):
        Parser.__init__(self, client, userid)
        self.scores = []
        self.current_sign = 1
        
    def ajouter(self, ref, signe=None):
        self.scores.append((self.current_sign if signe is None else signe, ref))

    def number(self, raw, number):
        if number < 0:
            self.ajouter(perso.Ref(abs(number), raw), -1)
        else:
            self.ajouter(perso.Ref(number, raw))
        self.current_sign = 1

    def sign(self, raw, sign):
        self.current_sign = sign

    def junk(self, raw):
        Parser.ignorer(self, raw)
        self.current_sign = 1

    def difficulte(self, raw, difficulte):
        self.ajouter(perso.Ref(difficulte.mod, difficulte.name), difficulte.sign)
        self.current_sign = 1

    def score(self, raw, ref):
        if ref.name != 'nom':
            if ref.is_int():
                if ref.auto_ref is not None:
                    self.ajouter(ref.auto_ref)
                self.ajouter(ref)
            else:
                self.ignorer(raw)
        self.current_sign = 1

class LanceParser(LanceJetParser):
    def __init__(self, client, userid):
        LanceJetParser.__init__(self, client, userid)
        self.des = None
        self.rolls = None
        self.result = None
        
    def finish(self):
        return self.des, self.rolls, self.result, self.scores, self.poubelle

    def dice(self, raw, dice_number, dice_type, bonus, malus):
        if self.des is None:
            self.rolls, _, self.result = regles.lance(dice_number, dice_type, bonus, malus)
            self.des = raw
        else:
            self.ignorer(raw)
        self.current_sign = 1

    def bonus(self, raw):
        LanceJetParser.bonus(self, raw)
        self.current_sign = 1

    def malus(self, raw):
        LanceJetParser.malus(self, raw)
        self.current_sign = 1

class CommandLance(Command):
    def __init__(self, client):
        Command.__init__(self, client)
        
    async def get_reply(self, message):
        if not message.content.startswith('lance'):
            return ()
        parser = LanceParser(self.client, message.author.id)
        des, dice, result, scores, poubelle = parser.parse(message.content[5:])
        if parser.dice is None:
            return (':warning: Lance quoi?',)
        score_total, sign, mod = regles.sum_scores(scores)
        final = result + score_total
        score_noms = ' '.join(f'{Command.str_sign(s) if i > 0 or s < 0 else ""} {score.name.capitalize()}' for i, (s, score) in enumerate(scores))
        score_valeurs = ' '.join(f'{Command.str_sign(s) if i > 0 or s < 0 else ""} {score.value}' for i, (s, score) in enumerate(scores))
        cont = f'{Command.perso_label(*parser.le_perso())} lance `{des} {score_noms} ({score_valeurs} = {Command.str_sign(sign)}{mod})`'
        if poubelle:
            cont += f' (inconnus: {", ".join(poubelle)})'
        cont += f'\n{Command.dice_icons(dice)}\n'
        cont += f'**{final}**'
        return (cont,)
        
class JetParser(LanceJetParser):
    def __init__(self, client, userid):
        LanceJetParser.__init__(self, client, userid)
        self.n_bonus = 0
        self.n_malus = 0
        
    def finish(self):
        return self.scores, self.n_bonus, self.n_malus, self.poubelle

    def dice(self, raw, dice_number, dice_type, bonus, malus):  
        self.ignorer(raw)
        self.current_sign = 1

    def bonus(self, raw):
        self.n_bonus += 1
        self.current_sign = 1

    def malus(self, raw):
        self.n_malus += 1
        self.current_sign = 1

class CommandJet(Command):
    MENTION_PATTERN = re.compile(r'^<@!\d+>$')
    
    def __init__(self, client):
        Command.__init__(self, client)

    async def get_reply(self, message):
        if not message.content.startswith('jet'):
            return ()
        parser = JetParser(self.client, message.author.id)
        scores, bonus, malus, poubelle = parser.parse(message.content[3:])
        le_perso, userid = parser.le_perso()
        if le_perso is None:
            return (':warning: Qui?',)
        sign, mod, dice, result, reussite = regles.jet(scores, bonus, malus)
        score_noms = ' '.join(f'{Command.str_sign(s) if i > 0 or s < 0 else ""} {score.name.capitalize()}' for i, (s, score) in enumerate(scores))
        score_valeurs = ' '.join(f'{Command.str_sign(s) if i > 0 or s < 0 else ""} {score.value}' for i, (s, score) in enumerate(scores))
        cont = f'{Command.perso_label(le_perso, userid)} fait un jet de ` {score_noms} ({score_valeurs} = {Command.str_sign(sign)}{mod})`'
        if bonus > 0:
            cont += f' avec {bonus} dé{"" if bonus == 1 else "s"} de bonus'
        if malus > 0:
            cont += f' {"et" if malus > 0 else "avec"} {malus} dé{"" if malus == 1 else "s"} de malus'
        if poubelle:
            cont += f' (inconnus: {", ".join(poubelle)})'
        cont += f'\n{Command.dice_icons(dice)}\n'
        cont += f'**{result}** **{reussite.name.capitalize()}**'
        return (cont,)

class CommandPurge(Command):
    def __init__(self, client):
        Command.__init__(self, client)
        
    async def get_reply(self, message):
        if message.content != 'purge':
            return ()
        await message.channel.delete_messages(self.client.message_queue)
        n = len(self.client.message_queue)
        self.client.message_queue = []
        return (f':x: {n} messages supprimés',)

class FDPParser(Parser):
    def __init__(self, client, userid):
        Parser.__init__(self, client, userid)
        
    def finish(self):
        return self.le_perso()

class CommandFDP(Command):
    def __init__(self, client):
        Command.__init__(self, client)
        
    async def get_reply(self, message):
        if not message.content.startswith('fdp'):
            return ()
        parser = FDPParser(self.client, message.author.id)
        le_perso, userid = parser.parse(message.content[3:])
        if le_perso is None:
            return (':warning: Qui?',)
        return (f'Fiche de perso de {Command.perso_label(le_perso, userid)}\n{le_perso.fiche()}',)

class PerdGagneParser(LanceParser):
    def __init__(self, client, userid):
        LanceParser.__init__(self, client, userid)
        self.le_score = None
        self.result = 0

    def difficulte(self, raw, difficulte):
        self.ignorer(raw)
        self.current_sign = 1

    def score(self, raw, ref):
        if self.le_score is None and ref.modifiable:
            if self.current_sign != 1:
                self.ignorer('-')
            self.le_score = ref
            self.current_sign = 1
        else:
            LanceParser.score(self, raw, ref)
            
    def finish(self):
        return self.le_score, self.des, self.rolls, self.result, self.scores, self.poubelle

class CommandPerdGagne(Command):
    def __init__(self, client):
        Command.__init__(self, client)
        
    async def get_reply(self, message):
        if message.content.startswith('perd'):
            sign_global = -1
            sign_str = 'perd'
        elif message.content.startswith('gagne'):
            sign_global = 1
            sign_str = 'gagne'
        else:
            return ()
        parser = PerdGagneParser(self.client, message.author.id)
        score, des, rolls, result, scores, poubelle = parser.parse(message.content[len(sign_str):])
        le_perso, userid = parser.le_perso()
        if le_perso is None:
            return (':warning: Qui?',)
        if score is None:
            return (':warning: Quoi?',)
        if des is None and len(scores) == 0:
            return (':warning: Combien?',)
        score_total, sign, mod = regles.sum_scores(scores)
        final = result + score_total
        score_noms = ' '.join(f'{Command.str_sign(s) if i > 0 or s < 0 else ""} {score.name.capitalize()}' for i, (s, score) in enumerate(scores))
        score_valeurs = ' '.join(f'{Command.str_sign(s) if i > 0 or s < 0 else ""} {score.value}' for i, (s, score) in enumerate(scores))
        cont = f'{Command.perso_label(le_perso, userid)} {sign_str} `{"" if des is None else des} {score_noms} ({score_valeurs} = {Command.str_sign(sign)}{mod})` en **{score.name.capitalize()}** ({score.value})'
        if poubelle:
            cont += f' (inconnus: {", ".join(poubelle)})'
        if des is not None:
            cont += f'\n{Command.dice_icons(rolls)}'
        score.value = max(min(int(score.value) + sign_global * final, score.max), 0)
        cont += f'\n**{final}**\n**{score.name.capitalize()} = {score.value}**'
        return (cont,)


class BoLClient(discord.Client):
    def __init__(self, pj_path):
        discord.Client.__init__(self)
        self.message_queue = []
        self.pj_par_userid = {}
        self.persos_par_nom = {}
        for pj, path in perso.load(pj_path):
            userid = int(os.path.basename(path)[:-4])
            self.pj_par_userid[userid] = pj
            self.persos_par_nom[pj.nom.value.lower()] = pj
        self.commands = tuple(ctor(self) for ctor in (CommandLance, CommandPurge, CommandFDP, CommandJet, CommandPerdGagne))
        
    async def on_ready(self):
        print (f'{self.user} has connected to Discord!')
    
    async def on_error(self, event, *args, **_):
        if event == 'on_message':
            print (f'Unhandled message: {args[0]}')
        raise
    
    async def reply(self, message, content):
        r = await message.channel.send(content)
        self.message_queue.append(r)
        
    async def on_message(self, message):
        if message.author.bot:
            return
        for cmd in self.commands:
            contents = await cmd.get_reply(message)
            if len(contents) > 0:
                self.message_queue.append(message)
                for content in contents:
                    reply = await message.channel.send(content)
                    self.message_queue.append(reply)
                break
        else:
            print (f'{message}\n    {message.content}')

client = BoLClient('data/PJ')
print (client.persos_par_nom)
print (client.pj_par_userid)
client.run(TOKEN)
