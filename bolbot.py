#!/bin/env python3

import os
import discord
import dotenv
import re
import perso
import regles
import util
import collections

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
            regles.DICE_PATTERN,
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

    def __init__(self, client, userid, n_perso=1):
        self.poubelle = []
        self.client = client
        self.persos = []
        self.mention(str(userid), userid)
        self.n_perso = n_perso

    def ignorer(self, raw):
        self.poubelle.append(raw)

    def les_persos(self):
        result = list((p, u) for p, u in reversed(self.persos) if p is not None)
        result.extend((p, u) for p, u in reversed(self.persos) if p is None and u is not None)
        result.extend(((None, None), (None, None)))
        return result

    def le_perso(self):
        return self.les_persos()[self.n_perso - 1]

    def lautre_perso(self):
        return self.les_persos()[0]

    def auth_perso(self, message, le_perso=None, userid=None):
        if le_perso is None and userid is None:
            le_perso, userid = self.le_perso()
        if message.author.id == self.client.mj_userid:
            return True
        if userid is not None and userid == message.author.id:
            return True
        if le_perso is self.client.persos_par_nom[message.author.id]:
            return True
        return False

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
        if util.snorm(raw) in regles.Difficulte.MAP:
            self.difficulte(raw, regles.Difficulte.MAP[raw])
        elif self.client.has_perso(raw):
            self.persos.append((self.client.get_perso(raw), None))
        else:
            le_perso, _uid = self.le_perso()
            if le_perso is not None:
                norm = util.snorm(raw)
                if norm in le_perso.ref_map:
                    self.score(raw, le_perso.ref_map[raw])
                elif norm in le_perso.avantages.value:
                    self.bonus(raw)
                elif norm in le_perso.desavantages.value:
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
    DIGITS = (None, '<:die_1:710969366786867230>', '<:die_2:710969366794993724>', '<:die_3:710969366925279273>', '<:die_4:710969366644260975>', '<:die_5:710969366417506386>', '<:die_6:710969366421700662>')
    MJ_ONLY_MESSAGE = ':no_entry: :raised_hand: :stop_sign: :middle_finger: :no_pedestrians:'

    def __init__(self, client, mj_command=True):
        self.client = client
        self.mj_command = mj_command

    async def auth_reply(self, message):
        if self.mj_command and message.author.id != self.client.mj_userid:
            return (Command.MJ_ONLY_MESSAGE,)
        return await self.get_reply(message)

    async def get_reply(self, message):
        raise NotImplementedError()

    def help(self):
        return f'{self} help not available'

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
        return ' '.join(Command.DIGITS[n] for n in dice)


class LanceJetParser(Parser):
    def __init__(self, client, userid, n_perso=1):
        Parser.__init__(self, client, userid, n_perso)
        self.scores = []
        self.current_sign = 1

    def ajouter(self, raw, ref, signe=None):
        if signe is None:
            signe = self.current_sign
        e = (signe, ref)
        if e in self.scores:
            if raw is not None:
                self.ignorer(raw)
        else:
            self.scores.append(e)

    def number(self, raw, number):
        if number < 0:
            self.ajouter(raw, util.Ref(abs(number), raw), -1)
        else:
            self.ajouter(raw, util.Ref(number, raw))
        self.current_sign = 1

    def sign(self, raw, sign):
        self.current_sign = sign

    def junk(self, raw):
        Parser.ignorer(self, raw)
        self.current_sign = 1

    def difficulte(self, raw, difficulte):
        self.ajouter(raw, util.Ref(difficulte.mod, difficulte.name), difficulte.sign)
        self.current_sign = 1

    def score(self, raw, ref):
        if ref.name != 'nom':
            if ref.is_int():
                if ref.auto_ref is not None:
                    self.ajouter(None, ref.auto_ref)
                self.ajouter(raw, ref)
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
        Command.__init__(self, client, False)

    async def get_reply(self, message):
        if not message.content.startswith('lance'):
            return ()
        parser = LanceParser(self.client, message.author.id)
        des, dice, result, scores, poubelle = parser.parse(message.content[5:])
        if not parser.auth_perso(message):
            return (Command.MJ_ONLY_MESSAGE,)
        if parser.dice is None:
            return (':warning: Lance quoi?',)
        score_total, sign, mod = regles.sum_scores(scores)
        final = result + score_total
        score_noms = ' '.join(f'{Command.str_sign(s) if i > 0 or s < 0 else ""} {score.name.capitalize()}' for i, (s, score) in enumerate(scores))
        score_valeurs = ' '.join(f'{Command.str_sign(s) if i > 0 or s < 0 else ""} {score.value}' for i, (s, score) in enumerate(scores))
        cont = f'{Command.perso_label(*parser.le_perso())} lance `{des} {score_noms} ({score_valeurs} = {Command.str_sign(sign)}{mod})`'
        if len(poubelle):
            cont += f' (ignoré: {", ".join(poubelle)})'
        cont += f'\n{Command.dice_icons(dice)}\n'
        cont += f'**{final}**'
        return (cont,)

    def help(self):
        return '`lance NdX [SCORES] [+|-N] [bonus|malus]`\nLance `N` dés de type `X`. Applique aussi les modificateur `SCORES` (attribut, aptitude de combat ou carrière), `+N` ou `-N` et les dés de `bonus` ou `malus`.\nLe bot répond avec les dés lancés et le résultat numérique.'


class JetParser(LanceJetParser):
    def __init__(self, client, userid, n_perso=1):
        LanceJetParser.__init__(self, client, userid, n_perso)
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
    def __init__(self, client):
        Command.__init__(self, client, False)

    async def get_reply(self, message):
        if not message.content.startswith('jet'):
            return ()
        parser = JetParser(self.client, message.author.id)
        scores, bonus, malus, poubelle = parser.parse(message.content[3:])
        le_perso, userid = parser.le_perso()
        if le_perso is None:
            return (':warning: Qui?',)
        if not parser.auth_perso(message, le_perso, userid):
            return (Command.MJ_ONLY_MESSAGE,)
        sign, mod, dice, result, reussite = regles.jet(scores, bonus, malus)
        score_noms = ' '.join(f'{Command.str_sign(s) if i > 0 or s < 0 else ""} {score.name.capitalize()}' for i, (s, score) in enumerate(scores))
        score_valeurs = ' '.join(f'{Command.str_sign(s) if i > 0 or s < 0 else ""} {score.value}' for i, (s, score) in enumerate(scores))
        cont = f'{Command.perso_label(le_perso, userid)} fait un jet de ` {score_noms} ({score_valeurs} = {Command.str_sign(sign)}{mod})`'
        if bonus > 0:
            cont += f' avec {bonus} dé{"" if bonus == 1 else "s"} de bonus'
        if malus > 0:
            cont += f' {"et" if malus > 0 else "avec"} {malus} dé{"" if malus == 1 else "s"} de malus'
        if len(poubelle) > 0:
            cont += f' (ignoré: {", ".join(poubelle)})'
        cont += f'\n{Command.dice_icons(dice)}\n'
        cont += f'**{result}** **{reussite.name.capitalize()}**'
        return (cont,)

    def help(self):
        return '`jet [PERSO] [ATTRIBUT] [APTITUDE] [CARRIÈRE] [+|- N] [bonus|malus]`\nEffectue un jet pour son personage (ou `PERSO`) avec les scores `ATTRIBUT`, `APTITUDE` (de combat) et/ou `CARRIÈRE`. Applique aussi le modificateur `+N` ou `-N` et les dés de `bonus` ou `malus`.\nLe bot répond avec les dés lancés, le résultat numérique et si le jet est réussi ou non.'


class Arme:
    TOUTES = collections.OrderedDict()

    def __init__(self, name, degats, aptitude, *keys):
        self.name = name
        self.degats = degats
        self.aptitude = aptitude
        self.parsed_degats = regles.parse_dice(degats)
        Arme.TOUTES[util.snorm(name)] = self
        for k in keys:
            Arme.TOUTES[util.snorm(k)] = self
        self.keys = keys

    def bonus_vigueur(self, aptitude):
        raise NotImplementedError()


class MainsNues(Arme):
    def __init__(self, name, *keys):
        Arme.__init__(self, name, '1d3', 'melee', *keys)

    def bonus_vigueur(self, aptitude):
        return 'vigueur/2'


class ArmeOutil(Arme):
    def __init__(self, name, degats, aptitude, *keys):
        Arme.__init__(self, name, degats, aptitude, *keys)

    def bonus_vigueur(self, aptitude):
        if aptitude == 'melee':
            return 'vigueur'
        return 'vigueur/2'


class ArmeImprovisee(ArmeOutil):
    def __init__(self, name, aptitude, *keys):
        ArmeOutil.__init__(self, name, '1d3', aptitude, *keys)


class ArmeLegere(ArmeOutil):
    def __init__(self, name, aptitude, *keys):
        ArmeOutil.__init__(self, name, '1d6M', aptitude, *keys)


class ArmeMoyenne(ArmeOutil):
    def __init__(self, name, aptitude, *keys):
        ArmeOutil.__init__(self, name, '1d6', aptitude, *keys)


class ArmeLourde(ArmeOutil):
    def __init__(self, name, aptitude, *keys):
        ArmeOutil.__init__(self, name, '1d6B', aptitude, *keys)


MainsNues('mains nues', 'mainsnues', 'mains', 'poings', 'pieds', 'main', 'poing', 'pied', 'rien', 'aucune')
ArmeImprovisee('arme improvisée', None, 'improvisée', 'improvisee', 'impro', 'caillou', 'pierre')
ArmeLegere('arme légère', None, 'légère', 'légere', 'legère', 'legere')
ArmeMoyenne('arme moyenne', None, 'moyenne')
ArmeLourde('arme lourde', None, 'lourde')
ArmeLegere('dague', None)
ArmeLegere('gourdin', 'melee')
ArmeLegere('rapière', 'melee', 'rapiere')
ArmeLegere('fronde', 'tir')
ArmeLegere('javelot', 'tir')
ArmeLegere('fléchette', 'tir', 'flechette', 'dard')
ArmeMoyenne('bâton', 'melee', 'baton')
ArmeMoyenne('épée', 'melee', 'épee', 'epée', 'epee', 'sword')
ArmeMoyenne('fléau', 'melee', 'fleau')
ArmeMoyenne('hache', None, 'axe')
ArmeMoyenne('lance', None)
ArmeMoyenne('masse d\'armes', None, 'masse')
ArmeMoyenne('massue', None)
ArmeMoyenne('arbalète', 'tir', 'arbalete')
ArmeMoyenne('arc', 'tir')
ArmeLourde('arme d\'hast', 'melee', 'hast')
ArmeLourde('épée à deux mains', 'melee', 'deux mains', 'deux mains', 'deux')
ArmeLourde('grande hache', 'melee', 'grande')
ArmeLourde('morgenstern', 'melee')
ArmeLourde('arbalète lourde', 'tir', 'balliste')


class FrappeParser(JetParser):
    def __init__(self, client, userid):
        JetParser.__init__(self, client, userid, 2)
        self.arme = None

    def junk(self, raw):
        if raw in Arme.TOUTES:
            self.arme = raw
        else:
            self.ignorer(raw)
        self.current_sign = 1


class CommandFrappe(Command):
    def __init__(self, client):
        Command.__init__(self, client, False)

    async def get_reply(self, message):
        if message.content.startswith('frappe'):
            skip = 6
            apt = 'melee'
        elif message.content.startswith('tire'):
            skip = 4
            apt = 'tir'
        else:
            return ()
        parser = FrappeParser(self.client, message.author.id)
        parser.parse(message.content[skip:])
        le_perso, userid = parser.le_perso()
        if not parser.auth_perso(message, le_perso, userid):
            return (Command.MJ_ONLY_MESSAGE,)
        lautre_perso, userid2 = parser.lautre_perso()
        if le_perso is None:
            return (':warning: Qui frappe?',)
        if lautre_perso is None:
            return (':warning: Frappe qui?',)
        if parser.arme is None:
            return (':warning: Avec quoi?',)
        arme = Arme.TOUTES[parser.arme]
        if arme.aptitude is not None:
            apt = arme.aptitude
        parser.score(f'{apt}', le_perso.ref_map[apt])
        parser.ajouter(f'défense ({lautre_perso.nom.value})', lautre_perso.aptitudes_combat.defense, -1)
        if f'arme favorite ({arme.name})' in le_perso.avantages.value:
            parser.bonus('arme favorite')
        scores, bonus, malus, poubelle = parser.finish()
        sign, mod, dice, result, reussite = regles.jet(scores, bonus, malus)
        score_noms = ' '.join(f'{Command.str_sign(s) if i > 0 or s < 0 else ""} {score.name.capitalize()}' for i, (s, score) in enumerate(scores))
        score_valeurs = ' '.join(f'{Command.str_sign(s) if i > 0 or s < 0 else ""} {score.value}' for i, (s, score) in enumerate(scores))
        cont = f'{Command.perso_label(le_perso, userid)} {"tire sur" if apt == "tir" else "frappe"} {Command.perso_label(lautre_perso, userid2)} avec {arme.name.capitalize()} ` {score_noms} ({score_valeurs} = {Command.str_sign(sign)}{mod})`'
        if bonus > 0:
            cont += f' avec {bonus} dé{"" if bonus == 1 else "s"} de bonus'
        if malus > 0:
            cont += f' {"et" if malus > 0 else "avec"} {malus} dé{"" if malus == 1 else "s"} de malus'
        if len(poubelle) > 0:
            cont += f' (ignoré: {", ".join(poubelle)})'
        cont += f'\n{Command.dice_icons(dice)}\n'
        cont += f'**{result}** **{reussite.name.capitalize()}**'
        if reussite.succes:
            dg_dice, _, dg_result = regles.lance(**arme.parsed_degats)
            bv = arme.bonus_vigueur(apt)
            bvn = le_perso.ref_map[bv].value
            if apt == 'tir' and 'tireur puissant' in le_perso.avantages.value:
                cont += f'\n\n**Dégâts** `{arme.degats} + {bv.capitalize()} ({bvn}) + Tireur puissant ({le_perso.attributs.vigueur.value})`\n{Command.dice_icons(dg_dice)}\n'
                dg_result += le_perso.attributs.vigueur.value
            else:
                cont += f'\n\n**Dégâts** `{arme.degats} + {bv.capitalize()} ({bvn})`\n{Command.dice_icons(dg_dice)}\n'
            dg_result += bvn
            cont += f'**{dg_result}**\n'
            lautre_perso.vitalite.value -= dg_result
            cont += f'{Command.perso_label(lautre_perso, userid2)}: {lautre_perso.vitalite.value} PV {"" if lautre_perso.vitalite.value > 0 else ":skull_crossbones:"}'
        return (cont,)

    def help(self):
        return '`frappe|tire [ATT] DÉF ARME`\nEffectue une frappe avec son perso (ou `ATT`) sur le personnage `DÉF` avec l\'arme `ARME`. Le bot effectue un jet de l\'aptitude de combat approprié, si le jet est réussi alors le bot effectue un jet de dommages et retire la vitalité.'


class CommandPurge(Command):
    def __init__(self, client):
        Command.__init__(self, client, True)

    async def get_reply(self, message):
        if message.content != 'purge':
            return ()
        await message.channel.delete_messages(self.client.message_queue)
        n = len(self.client.message_queue)
        self.client.message_queue = []
        return (f':x: {n} messages supprimés',)

    def help(self):
        return '`purge`\nSupprime les messages de ce bot ainsi que les requêtes des PJ/MJ.'


class FDPParser(Parser):
    def __init__(self, client, userid):
        Parser.__init__(self, client, userid)

    def finish(self):
        return self.le_perso()


class CommandFDP(Command):
    def __init__(self, client):
        Command.__init__(self, client, False)

    async def get_reply(self, message):
        if not message.content.startswith('fdp'):
            return ()
        parser = FDPParser(self.client, message.author.id)
        le_perso, userid = parser.parse(message.content[3:])
        if not parser.auth_perso(message, le_perso, userid):
            return (Command.MJ_ONLY_MESSAGE,)
        if le_perso is None:
            return (':warning: Qui?',)
        return (f'Fiche de perso de {Command.perso_label(le_perso, userid)}\n{le_perso.fiche()}',)

    def help(self):
        return '`fdp [PERSO]`\nAffiche une jolie fiche de personnage pour son perso (ou celui de `PERSO`).'


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
        Command.__init__(self, client, True)

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

    def help(self):
        return '`perd|gagne [PERSO] SCORE [N] [DÉS]`\nModifie un score `SCORE` de son perso (ou celui de `PERSO`). L\'utilisation de `perd` diminue le score, alors que `gagne` augmente le score.\nLa quantité perdue ou gagnée est soit un nombre (`N`) soit une expression de dés (`DÉS`)'


class CommandPNJ(Command):
    def __init__(self, client):
        Command.__init__(self, client)

    async def get_reply(self, message):
        if not message.content.startswith('pnj', True):
            return ()
        pnj = perso.Perso()
        for line in message.content[3:].split('\n'):
            pnj.parse_line(line.strip())
        self.client.add_perso(pnj)
        return (f'Fiche de perso de {Command.perso_label(pnj, None)}\n{pnj.fiche()}',)

    def help(self):
        return '`pnj ...`\nCrée un nouveau PNJ. La suite du message doit être sous la forme `STAT: VALEUR` ou `NIVEAU NOM VAEA IMTD VIT`.'


class CloneParser(Parser):
    def __init__(self, client, userid):
        Parser.__init__(self, client, userid)
        self.nombre = -1

    def number(self, raw, number):
        self.nombre = number

    def finish(self):
        return self.le_perso()[0], self.nombre


class CommandClone(Command):
    def __init__(self, client):
        Command.__init__(self, client)

    async def get_reply(self, message):
        if not message.content.startswith('clone', True):
            return ()
        parser = CloneParser(client, message.author.id)
        le_perso, nombre = parser.parse(message.content[5:])
        if le_perso is None:
            return (':warning: Qui?',)
        if nombre <= 0:
            return (':warning: Combien?',)
        noms = []
        for n in range(nombre):
            pnj = le_perso.clone()
            pnj.nom.value += str(n + 2)
            noms.append(pnj.nom.value)
            self.client.add_perso(pnj)
        return (f'Le personnage {Command.perso_label(le_perso, None)} a été cloné {nombre} fois\n{", ".join(noms)}',)

    def help(self):
        return '`clone PERSO N`\nCrée `N` copies exactes du personage `PERSO`. Le nom de chacun des personages issues de la copie est augmenté d\'un nombre de 2 à `N`.'


class CommandListe(Command):
    def __init__(self, client):
        Command.__init__(self, client, True)

    async def get_reply(self, message):
        if not message.content.startswith('liste'):
            return ()
        return ('\n'.join(f'**{p.nom.value}** ({p.niveau.value})' for p in sorted(self.client.persos_par_nom.values(), key=(lambda p: p.niveau.value))),)

    def help(self):
        return '`liste`\nAffiche la liste des personnages que ce bot connait.'


class CommandAide(Command):
    def __init__(self, client):
        Command.__init__(self, client, False)

    async def get_reply(self, message):
        if not message.content.startswith('aide'):
            return ()
        return ('\n\n'.join(c.help() for c in self.client.commands if message.author.id == self.client.mj_userid or not c.mj_command),)

    def help(self):
        return '`aide`\nAffiche cette aide.'


class BoLClient(discord.Client):
    def __init__(self, mj_file, pj_path, pnj_path):
        discord.Client.__init__(self)
        self.message_queue = []
        self.pj_par_userid = {}
        self.persos_par_nom = {}
        with open(mj_file) as f:
            self.mj_userid = int(f.read().strip())
        for pj, path in perso.load(pj_path):
            pj.niveau.value = 'pj'
            userid = int(os.path.basename(path)[:-4])
            self.pj_par_userid[userid] = pj
            self.add_perso(pj)
        for pnj, path in perso.load(pnj_path):
            self.add_perso(pnj)
        self.commands = tuple(ctor(self) for ctor in (CommandLance, CommandPurge, CommandFDP, CommandJet, CommandPerdGagne, CommandPNJ, CommandClone, CommandListe, CommandFrappe, CommandAide))

    def add_perso(self, p):
        self.persos_par_nom[util.snorm(p.nom.value)] = p

    def get_perso(self, nom):
        return self.persos_par_nom[util.snorm(nom)]

    def has_perso(self, nom):
        return util.snorm(nom) in self.persos_par_nom

    async def on_ready(self):
        print(f'{self.user} has connected to Discord!')

    async def on_error(self, event, *args, **_):
        if event == 'on_message':
            print(f'Unhandled message: {args[0]}')
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
            pass


client = BoLClient('data/MJ', 'data/PJ', 'data/PNJ')
print(client.persos_par_nom)
print(client.pj_par_userid)
client.run(TOKEN)
