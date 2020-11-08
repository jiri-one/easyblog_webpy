#!/usr/bin/python2
# -*- coding: utf-8 -*-

import web, datetime, unicodedata, markdown

web.config.debug = False #vypnuti debugovani, kvuli funkcnim sessions

#nastaveni
urls = ("/", "Index",
        "/(\d+)", "Zobraz",
        "/admin/edituj/(.*)", "Edituj",
        "/hledej", "Hledej",
        "/admin/smaz/(.*)", "Smaz",
        "/admin/komentare", "Komentare",
        "/admin/komentare/edituj/(\d+)", "Komentar_edituj",
        "/admin/komentare/smaz/(\d+)", "Komentar_smaz",
        "/admin/kategorie", "Kategorie_admin",
        "/admin/upload", "Upload",
        "/admin", "Admin",
        "/kategorie/(.*)", "Kategorie",
        "/strana/(\d+)", "Strankovani_indexu",
        "/(.*)", "Stranka") #pouzite adresy

sablona = web.template.render("/srv/http/virtual/jiri.one/sablony/", base="base") #sablony pro design
databaze = web.database(dbn="sqlite", db="/srv/db/muj_blog.db") #nastaveni databaze
web.template.Template.globals['get_seznam_kategorii'] = lambda: databaze.select("kategorie", order="cislo ASC").list() #je tu jen proto, aby se do base sablony dostal seznam kategorii z databaze; lamda funkce zajistuje znovunacteni seznamu kategorii
web.template.Template.globals['markdown'] = markdown.markdown #markdown umozni HTML syntaxi - do sablony pridat $:markdown(co_vykreslit)
app = web.application(urls, globals())
zapisku = 10 # pocet zapisku na stranku, jeste jednou nutne nastavit ve tride "Strankovani"
web.config.smtp_server = "10.0.0.10"
web.config.smtp_port = 25
web.config.smtp_username = "klerik"
web.config.smtp_password = "Pavouk+7"
web.config.smtp_starttls = True

application = app.wsgifunc() #pro spravnou funkci na Apache s mod_wsgi


#pomocne funkce
def ZISKEJ_ZAPISEK(cislo):
    try:
        return databaze.select("zapisky", where="cislo=$cislo", vars=locals())[0]
    except IndexError:
        return None

def ZISKEJ_ZAPISEK_Z_URL(url):
    try:
        return databaze.select("zapisky", where="url=$url", vars=locals())[0]
    except IndexError:
        return None

def AKTUALIZUJ_ZAPISEK(cislo, nadpis, url, obsah, kategorie_zapisku):
    databaze.update('zapisky', where="cislo=$cislo", nadpis=nadpis, url=url, obsah=obsah, kategorie=kategorie_zapisku, vars=locals())

def SMAZ_ZAPISEK(url):
    databaze.delete("zapisky", where="url=$url", vars=locals())

def ZISKEJ_KOMENTAR(cislo):
    try:
        return databaze.select("komentare", where="cislo=$cislo", vars=locals())[0]
    except IndexError:
        return None

def AKTUALIZUJ_KOMENTAR(cislo, nadpis, nick, obsah):
    databaze.update('komentare', where="cislo=$cislo", vars=locals(), nadpis=nadpis, nick=nick, obsah=obsah)

def SMAZ_KOMENTAR(cislo):
    databaze.delete("komentare", where="cislo=$cislo", vars=locals())

def SMAZ_KOMENTARE_SE_ZAPISKEM(url):
    cislo = databaze.select("zapisky", where="url=$url", vars=locals())[0]["cislo"]
    databaze.delete("komentare", where="cislo_zapisku=$cislo", vars=locals())

def remove_diacritic(input):
    """Odebere diakritiku z INPUT"""
    vysledek = unicode(unicodedata.normalize('NFKD', input).encode('ASCII', 'ignore'))
    vysledek = vysledek.lower();
    vysledek = vysledek.replace(" ", "-")
    vysledek = vysledek.replace("!", "")
    vysledek = vysledek.replace("?", "")
    vysledek = vysledek.replace("\"", "")
    vysledek = vysledek.replace("/", "")
    vysledek = vysledek.replace(",", "-")
    vysledek = vysledek.replace(".", "-")
    vysledek = vysledek.replace("--", "-")
    vysledek = vysledek.replace("  ", " ")
    return vysledek


def ziskej_kategorie(zapisek):
    kategorie = u"<div class=\"zarazen_do\">Zařazen do: "
    kategorie_nerozdelene = unicode(zapisek.get("kategorie"))
    kategorie_split = kategorie_nerozdelene.split(";")
    for jedna_kategorie in kategorie_split[0:len(kategorie_split)-1]:
        kategorie = kategorie + u"<a href=\"/kategorie/" + ziskej_url_kategorie(jedna_kategorie) + u"\">" + jedna_kategorie + "</a>, "
    kategorie_a_cas = kategorie[0:-2] + u" — Jiri @ " + zapisek.zadano_kdy[11:-3] + u"</div>"
    return kategorie_a_cas

def ziskej_url_kategorie(kategorie):
    try:
        cela_kategorie = databaze.select(u"kategorie", where=u"kategorie=$kategorie", vars=locals())[0]
        return unicode(cela_kategorie.get(u"url_kategorie"))
    except IndexError:
        return "KATEGORIE_UZ_NEEXISTUJE"

def ziskej_kategorii_z_url(url_kategorie):
    try:
        cela_kategorie = databaze.select("kategorie", where="url_kategorie=$url_kategorie;", vars=locals())[0]
        return unicode(cela_kategorie.get("kategorie"))
    except IndexError:
        return None

def ziskej_kategorii_z_cisla(cislo_kategorie):
    try:
        cela_kategorie = databaze.select("kategorie", where="cislo=$cislo_kategorie;", vars=locals())[0]
        return cela_kategorie
    except IndexError:
        return None

def vytvor_formular_kategorii(formular):
    zacatek_radku = 0
    konec_radku = 6
    seznam_prvku_formulare = []
    while len(formular.inputs) > zacatek_radku:
        seznam_prvku_formulare.append(u"<tr>")
        for input in formular.inputs[zacatek_radku:konec_radku]:
            seznam_prvku_formulare.append(u"<td>" + input.render() + u"</td>")
        zacatek_radku = zacatek_radku + 6
        konec_radku = konec_radku + 6
        seznam_prvku_formulare.append(u"</tr>")
    return seznam_prvku_formulare

def vytvor_formular_administrace(formular):
    pocet = databaze.query("SELECT COUNT(*) AS kategorii FROM kategorie")[0]
    seznam_prvku_formulare = []
    seznam_prvku_formulare.append(u"<tr>")
    for input in formular.inputs[:pocet.kategorii]: #vlozi vsechny checkboxy kategorii
        seznam_prvku_formulare.append(u"<td>" + input.render() + input.description + u"</td>")
    seznam_prvku_formulare.append(u"</tr><tr><td colspan=\"" + unicode(pocet.kategorii) + "\">&nbsp;&nbsp;</td></tr>")
    for input in formular.inputs[pocet.kategorii:]: #vlozi zbytek formulare
        seznam_prvku_formulare.append(u"<tr><td colspan=\"" + unicode(pocet.kategorii) + "\">" + input.description + input.render() + u"</td></tr>")                
    return seznam_prvku_formulare

def ziskej_datum(datum):
    rok = datum[0:4]
    mesic = datum[5:7]
    den = int(datum[-2:])
    if mesic == "01":
        mesic = u"Leden"
    elif mesic == "02":
        mesic = u"Únor"
    elif mesic == "03":
        mesic = u"Březen"
    elif mesic == "04":
        mesic = u"Duben"
    elif mesic == "05":
        mesic = u"Květen"
    elif mesic == "06":
        mesic = u"Červen"
    elif mesic == "07":
        mesic = u"Červenec"
    elif mesic == "08":
        mesic = u"Srpen"
    elif mesic == "09":
        mesic = u"Září"
    elif mesic == "10":
        mesic = u"Říjen"
    elif mesic == "11":
        mesic = u"Listopad"
    elif mesic == "12":
        mesic = u"Prosinec"
    datum = unicode(den) + ". " + mesic + ", " + rok
    return datum

def vyhledavani(slovo, limit, offset):
    slovo = "%" + slovo + "%"
    vysledek = databaze.query("SELECT * FROM zapisky WHERE nadpis LIKE $slovo OR obsah LIKE $slovo ORDER BY cislo DESC LIMIT $offset,$limit", vars=locals())
    pocet = databaze.query("SELECT COUNT(*) AS zapisku FROM zapisky WHERE nadpis LIKE $slovo OR obsah LIKE $slovo", vars=locals())[0]
    if bool(vysledek) != 0:
        return vysledek, pocet
    else:
        vysledek = "nic nenalezeno"
        return vysledek, pocet

def vyhledavani_v_kategoriich(kategorie, limit, offset):
    kategorie = unicode("%" + kategorie + ";%")
    vysledek = databaze.query("SELECT * FROM zapisky WHERE kategorie LIKE $kategorie ORDER BY cislo DESC LIMIT $offset,$limit;", vars=locals())
    pocet = databaze.query("SELECT COUNT(*) AS zapisku FROM zapisky WHERE kategorie LIKE $kategorie;", vars=locals())[0]
    if bool(vysledek) != 0:
        return vysledek, pocet
    else:
        vysledek = unicode("Kategorie buď neexistuje a nebo neobsahuje žádné zápisky.")
        return vysledek, pocet

#Odsud jsou definovany samotne tridy

class Index():
    def GET(self):
        seznam_zapisku = databaze.select("zapisky", order="cislo DESC", limit= "$zapisku", vars=globals())
        stranky = "index"
        cislo_strany = "index"
        return sablona.index(seznam_zapisku, ziskej_kategorie, ziskej_datum, stranky, cislo_strany)

class Strankovani_indexu:
    def GET(self, cislo_strany):
        zapisku = 10
        offset = (int(cislo_strany) - 1) * zapisku
        seznam_zapisku = databaze.select("zapisky", order="cislo DESC", limit="$zapisku", offset="$offset", vars=locals())
        pocet = databaze.query("SELECT COUNT(*) AS zapisku FROM zapisky")[0]
        stranky = pocet.zapisku / zapisku
        if pocet.zapisku % zapisku > 0:
            stranky += 1
        return sablona.index(seznam_zapisku, ziskej_kategorie, ziskej_datum, stranky, cislo_strany)

class Hledej:
    """Trida pro vyhledavani na webu."""
    form_hledej = web.form.Form(
    web.form.Textbox("vyhledavani", size=10, description=""),
    web.form.Button("Vyhledat")
    ) # Formular pro vyhledavani na webu
    def GET(self):
        input = web.input()
        if input:
            cislo_strany = input.strana if hasattr(input, "strana") else 1
            zapisku = 10
            offset = (int(cislo_strany) - 1) * zapisku
            form_hledej = Hledej.form_hledej()
            fraze = input.vyhledavani
            vysledky = vyhledavani(fraze, zapisku, offset)
            pocet = vysledky[1]
            stranky = pocet.zapisku / zapisku
            if pocet.zapisku % zapisku > 0:
                stranky += 1
            if stranky == 0:
                stranky += 1
            typ_vysledku = unicode(type(vysledky[0]))
            if typ_vysledku == "<type \'instance\'>":
                typ = 1
            else:
                typ = 0
            return sablona.hledej(form_hledej, vysledky[0], typ, ziskej_kategorie, ziskej_datum, stranky, cislo_strany, fraze)
        else:
            return "Použíjte vyhledávání na hlavní stránce"
    def POST(self):
        input = web.input()
        fraze = input.vyhledavani
        raise web.seeother("/hledej?vyhledavani=" + fraze)

class Kategorie:
    def GET(self,kategorie):
        strankovani = web.input()
        cislo_strany = strankovani.strana if hasattr(strankovani, 'strana') else 1
        zapisku = 10
        offset = (int(cislo_strany) - 1) * zapisku
        kategorie = ziskej_kategorii_z_url(kategorie)
        if not kategorie:
            kategorie = "Zvolená kategorie (už) neexistuje, zobrazeny všechny kategorie."
            seznam_zapisku = databaze.select("zapisky", order="cislo DESC", limit="$zapisku", offset="$offset", vars=locals())
            pocet = databaze.query("SELECT COUNT(*) AS zapisku FROM zapisky")[0]
            stranky = pocet.zapisku / zapisku
            if pocet.zapisku % zapisku > 0:
                stranky += 1
            return sablona.kategorie(seznam_zapisku, ziskej_kategorie, ziskej_datum, stranky, cislo_strany, kategorie)
        else:
            seznam_zapisku = vyhledavani_v_kategoriich(kategorie, zapisku, offset)
            pocet = seznam_zapisku[1]
            seznam_zapisku = seznam_zapisku[0]
            stranky = pocet.zapisku / zapisku
            if pocet.zapisku % zapisku > 0:
                stranky += 1
            return sablona.kategorie(seznam_zapisku, ziskej_kategorie, ziskej_datum, stranky, cislo_strany, kategorie)

class Zobraz:
    """Trida pro zobrazeni jednoho zapisku pomoci cisla zapisku. (permalink)"""
    form_komentar = web.form.Form(
    web.form.Textbox("nadpis_komentare", web.form.notnull, size=50, description="Nadpis:"),
    web.form.Textbox("nick", web.form.notnull, size=50, description="Nick:"),
    web.form.Textbox("antispam", web.form.notnull, size=50, description="Antispam:", class_="cleardefault", value="Sem napište ČÍSLEM součet čísel dvě a tři (tedy pět ;-))"),
    web.form.Textarea("obsah", web.form.notnull, rows=8, cols=50, description="Obsah:"),
    web.form.Button("Odeslat"),
    validators = [web.form.Validator("Spatne jste vyplnili policko s antispamovou ochranou!", lambda i: int(i.antispam) == 5)]
    ) # Formular pro vytvoreni komentare
    def GET(self,cislo):
        form_komentar = self.form_komentar()
        zapisek = ZISKEJ_ZAPISEK(int(cislo))
        if not zapisek:
            raise web.seeother("/")
        seznam_komentaru = databaze.select("komentare", where="cislo_zapisku=$cislo", order="cislo ASC", vars=locals())
        return sablona.zobraz(zapisek, seznam_komentaru, form_komentar, ziskej_datum, ziskej_kategorie)
    def POST(self,cislo):
        form_komentar = self.form_komentar()
        zapisek = ZISKEJ_ZAPISEK(int(cislo))
        seznam_komentaru = databaze.select("komentare", where="cislo_zapisku=$cislo", order="cislo ASC", vars=locals())
        if not form_komentar.validates():
                return sablona.zobraz(zapisek, seznam_komentaru, form_komentar, ziskej_datum, ziskej_kategorie)
        else:
            cas = datetime.datetime.now()
            databaze.insert("komentare", nadpis = form_komentar.d.nadpis_komentare, nick = form_komentar.d.nick,
            obsah = form_komentar.d.obsah, zadano_kdy=datetime.datetime.combine(cas.date(), datetime.time(cas.hour, cas.minute, cas.second)), cislo_zapisku = int(cislo))
            zapisek.pocet_komentaru += 1
            databaze.update("zapisky", where="cislo=$zapisek.cislo", vars=locals(), pocet_komentaru=zapisek.pocet_komentaru)
            web.sendmail("komentare@klerik.cz", "klerik@klerik.cz", "Přidán nový komentář",
                         u"Pod zápisek " + u"<a href=\"http://jiri.one/" + unicode(zapisek.url) + u"\">" + unicode(zapisek.nadpis) + u"</a>"
                         + u"</br></br><b>Od:</b> " + unicode(form_komentar.d.nick)
                         + u"</br></br><b>Nadpis:</b> " + unicode(form_komentar.d.nadpis_komentare)
                         + u"</br></br><b>Text komentáře:</b> " + unicode(form_komentar.d.obsah),
                        headers=({"Content-Type": "text/html",}))
        raise web.seeother("/" + zapisek.url)

class Stranka:
    """Trida pro zobrazeni jednoho zapisku po zadani jeho URL."""
    def GET(self, url):
        form_komentar = Zobraz.form_komentar()
        zapisek = ZISKEJ_ZAPISEK_Z_URL(unicode(url))
        if not zapisek:
            raise web.seeother("/")
        cislo = zapisek.cislo
        seznam_komentaru = databaze.select("komentare", where="cislo_zapisku=$cislo", order="cislo ASC", vars=locals())
        return sablona.zobraz(zapisek, seznam_komentaru, form_komentar, ziskej_datum, ziskej_kategorie)
    def POST(self,url):
        form_komentar = Zobraz.form_komentar()
        zapisek = ZISKEJ_ZAPISEK_Z_URL(unicode(url))
        seznam_komentaru = databaze.select("komentare", where="cislo_zapisku=$zapisek.cislo", order="cislo ASC", vars=locals())
        if not form_komentar.validates():
                return sablona.zobraz(zapisek, seznam_komentaru, form_komentar, ziskej_datum, ziskej_kategorie)
        else:
            cas = datetime.datetime.now()
            databaze.insert("komentare", nadpis = form_komentar.d.nadpis_komentare, nick = form_komentar.d.nick,
            obsah = form_komentar.d.obsah, zadano_kdy=datetime.datetime.combine(cas.date(), datetime.time(cas.hour, cas.minute, cas.second)), cislo_zapisku = int(zapisek.cislo))
            zapisek.pocet_komentaru += 1
            databaze.update("zapisky", where="cislo=$zapisek.cislo", vars=locals(), pocet_komentaru=zapisek.pocet_komentaru)
            web.sendmail("komentare@klerik.cz", "klerik@klerik.cz", "Přidán nový komentář",
                         u"Pod zápisek " + u"<a href=\"http://jiri.one/" + unicode(zapisek.url) + u"\">" + unicode(zapisek.nadpis) + u"</a>"
                         + u"</br></br><b>Od:</b> " + unicode(form_komentar.d.nick)
                         + u"</br></br><b>Nadpis:</b> " + unicode(form_komentar.d.nadpis_komentare)
                         + u"</br></br><b>Text komentáře:</b> " + unicode(form_komentar.d.obsah),
                        headers=({"Content-Type": "text/html",}))
        raise web.seeother("/" + zapisek.url)

class Edituj:
    """Trida pro editaci jednoho zapisku."""
    def GET(self, url):
        if Admin.session.get('logged_in', False):
            zapisek = ZISKEJ_ZAPISEK_Z_URL(unicode(url))
            kategorie_nerozdelene = unicode(zapisek.get("kategorie"))
            kategorie_split = kategorie_nerozdelene.split(";")
            seznam_kategorii = databaze.select("kategorie", order="cislo DESC")
            form_edit = web.form.Form() # Formular pro editaci zapisku
            for checkbox in seznam_kategorii:
                form_edit.inputs = (form_edit.inputs + ((web.form.Checkbox(checkbox.url_kategorie, value=checkbox.url_kategorie, description=checkbox.kategorie, checked=(checkbox.kategorie in kategorie_split))),))
            form_edit.inputs = (form_edit.inputs + ((web.form.Textbox("nadpis", web.form.notnull, size=40, value=zapisek.nadpis, description="Nadpis:</br>")),))
            form_edit.inputs = (form_edit.inputs + ((web.form.Textbox("url", web.form.notnull, size=40, value=zapisek.url, description="URL adresa:</br>")),))
            form_edit.inputs = (form_edit.inputs + ((web.form.Textarea("obsah", web.form.notnull, rows=10, cols=80, value=zapisek.obsah, description="Obsah:</br>")),))
            form_edit.inputs = (form_edit.inputs + ((web.form.Button("Uprav")),))
            form_edit = vytvor_formular_administrace(form_edit)
            return sablona.edit(zapisek, form_edit)
        else:
            return "Nemate dostatecne opravneni!!!"

    def POST(self, url):
        if Admin.session.get('logged_in', False):
            zapisek = ZISKEJ_ZAPISEK_Z_URL(unicode(url))
            seznam_kategorii = databaze.select("kategorie", order="cislo DESC")
            kategorie_zapisku = unicode("")
            for kategorie in seznam_kategorii:
                checkbox = web.input() #asi lepsi dat nad cyklus for, pak to vyzkousej
                if checkbox.has_key(kategorie.url_kategorie) == True:
                    kategorie_zapisku = kategorie_zapisku + unicode(kategorie.kategorie) + ";"
            form_edit = web.form.Form() # Formular pro editaci zapisku
            form_edit.inputs = (form_edit.inputs + ((web.form.Textbox("nadpis", web.form.notnull, size=40)),))
            form_edit.inputs = (form_edit.inputs + ((web.form.Textbox("url", web.form.notnull, size=40)),))
            form_edit.inputs = (form_edit.inputs + ((web.form.Textarea("obsah", web.form.notnull, rows=10, cols=80)),))
            form_edit.inputs = (form_edit.inputs + ((web.form.Button("Uprav")),))
            if not form_edit.validates():
                return sablona.edit(zapisek, form_edit)
            AKTUALIZUJ_ZAPISEK(int(zapisek.cislo), form_edit.d.nadpis, remove_diacritic(form_edit.d.url), form_edit.d.obsah, kategorie_zapisku)
            raise web.seeother("/admin")
        else:
            return "Nemate dostatecne opravneni!!!"

class Smaz:
    """Trida pro zmazani jednoho zapisku."""
    form_smaz = web.form.Form(web.form.Button("Ano", value="Ano"), web.form.Button("Ne", value="Ne"))
    # Formular, kde jsou dve rozhodovaci tlacika pro smazani, hodnota "value" tam musi byt uvedena pro spravnou funkci dole
    def GET(self, url):
        if Admin.session.get('logged_in', False):
            form_smaz = self.form_smaz()
            return sablona.smaz(url, form_smaz)
        else:
            return "Nemate dostatecne opravneni!!!"
    def POST(self,url):
        if Admin.session.get('logged_in', False):
            form_smaz = self.form_smaz()
            if not form_smaz.validates():
                return sablona.smaz(url, form_smaz)
            if form_smaz.d.Ano:
                SMAZ_KOMENTARE_SE_ZAPISKEM(unicode(url))
                SMAZ_ZAPISEK(unicode(url))
                raise web.seeother("/admin")
            if form_smaz.d.Ne:
                raise web.seeother("/admin")
        else:
            return "Nemate dostatecne opravneni!!!"

class Kategorie_admin:
    """Trida pro administraci kategorii."""
    def GET(self):
        if Admin.session.get('logged_in', False):
            seznam_kategorii = databaze.select("kategorie", order="cislo ASC")
            form_kategorie = web.form.Form() # Formular pro vytvoreni noveho zapisku
            for kategorie in seznam_kategorii:
                form_kategorie.inputs = (form_kategorie.inputs + ((web.form.Textbox(u"cislo_" + unicode(kategorie.cislo), web.form.notnull, size=5, value=kategorie.cislo)),))
                form_kategorie.inputs = (form_kategorie.inputs + ((web.form.Textbox(u"kategorie_" + unicode(kategorie.cislo), web.form.notnull, size=15, value=kategorie.kategorie)),))
                form_kategorie.inputs = (form_kategorie.inputs + ((web.form.Textbox(u"url_kategorie_" + unicode(kategorie.cislo), web.form.notnull, size=15, value=kategorie.url_kategorie)),))
                form_kategorie.inputs = (form_kategorie.inputs + ((web.form.Textbox(u"popis_" + unicode(kategorie.cislo), web.form.notnull, size=50, value=kategorie.popis)),))
                form_kategorie.inputs = (form_kategorie.inputs + ((web.form.Button(u"uprav", value=u"uprav_" + unicode(kategorie.cislo))),))
                form_kategorie.inputs = (form_kategorie.inputs + ((web.form.Button(u"smaz", value=u"smaz_" + unicode(kategorie.cislo))),))
            form_kategorie.inputs = (form_kategorie.inputs + ((web.form.Textbox(u"cislo_nove", web.form.notnull, size=5, value=u"Nové číslo:")),))
            form_kategorie.inputs = (form_kategorie.inputs + ((web.form.Textbox(u"kategorie_nova", web.form.notnull, size=15, value=u"Nová kategorie:")),))
            form_kategorie.inputs = (form_kategorie.inputs + ((web.form.Textbox(u"url_kategorie_nova", web.form.notnull, size=15, value=u"URL nové kategorie:")),))
            form_kategorie.inputs = (form_kategorie.inputs + ((web.form.Textbox(u"popis_novy", web.form.notnull, size=50, value=u"Popis nové kategorie:")),))
            form_kategorie.inputs = (form_kategorie.inputs + ((web.form.Button(u"vloz", value=u"vloz")),))
            form_kategorie = vytvor_formular_kategorii(form_kategorie)
            return sablona.kategorie_admin(form_kategorie)
        else:
            return "Nemate dostatecne opravneni!!!"
    def POST(self):
        if Admin.session.get('logged_in', False):
            seznam_kategorii = databaze.select("kategorie", order="cislo DESC")
            form_kategorie = web.form.Form() # Formular pro vytvoreni noveho zapisku            
            for kategorie in seznam_kategorii:
                form_kategorie.inputs = (form_kategorie.inputs + ((web.form.Textbox(u"cislo_" + unicode(kategorie.cislo), web.form.notnull, size=5, value=kategorie.cislo)),))
                form_kategorie.inputs = (form_kategorie.inputs + ((web.form.Textbox(u"kategorie_" + unicode(kategorie.cislo), web.form.notnull, size=15, value=kategorie.kategorie)),))
                form_kategorie.inputs = (form_kategorie.inputs + ((web.form.Textbox(u"url_kategorie_" + unicode(kategorie.cislo), web.form.notnull, size=15, value=kategorie.url_kategorie)),))
                form_kategorie.inputs = (form_kategorie.inputs + ((web.form.Textbox(u"popis_" + unicode(kategorie.cislo), web.form.notnull, size=50, value=kategorie.popis)),))
                form_kategorie.inputs = (form_kategorie.inputs + ((web.form.Button(u"uprav", value=u"uprav_" + unicode(kategorie.cislo))),))
                form_kategorie.inputs = (form_kategorie.inputs + ((web.form.Button(u"smaz", value=u"smaz_" + unicode(kategorie.cislo))),))
            form_kategorie.inputs = (form_kategorie.inputs + ((web.form.Textbox(u"cislo_nove", web.form.notnull, size=5, value=u"Nové číslo:")),))
            form_kategorie.inputs = (form_kategorie.inputs + ((web.form.Textbox(u"kategorie_nova", web.form.notnull, size=15, value=u"Nová kategorie:")),))
            form_kategorie.inputs = (form_kategorie.inputs + ((web.form.Textbox(u"url_kategorie_nova", web.form.notnull, size=15, value=u"URL nové kategorie:")),))
            form_kategorie.inputs = (form_kategorie.inputs + ((web.form.Textbox(u"popis_novy", web.form.notnull, size=50, value=u"Popis nové kategorie:")),))
            form_kategorie.inputs = (form_kategorie.inputs + ((web.form.Button(u"vloz", value=u"vloz")),))
            form_kategorie = vytvor_formular_kategorii(form_kategorie)
            input = web.input()
            try:
                if input.uprav:
                    cislo_kategorie = unicode(input.uprav)
                    cislo_kategorie = cislo_kategorie.split("_")[1]
                    cela_kategorie = ziskej_kategorii_z_cisla(cislo_kategorie)
                    jmeno_kategorie = cela_kategorie.kategorie
                    cislo_nove = input.get("cislo_" + cislo_kategorie)
                    kategorie_nova = input.get("kategorie_" + cislo_kategorie)
                    url_kategorie_nova = input.get("url_kategorie_" + cislo_kategorie)
                    popis_novy = input.get("popis_" + cislo_kategorie)

                    kategorie = unicode("%" + jmeno_kategorie + ";%")
                    zapisky_v_kategorii = databaze.query("SELECT * FROM zapisky WHERE kategorie LIKE $kategorie ORDER BY cislo DESC", vars=locals())
                    for zapisek in zapisky_v_kategorii:
                        kategorie_zapisku = unicode("")
                        kategorie_nerozdelene = unicode(zapisek.kategorie)
                        kategorie_split = kategorie_nerozdelene.split(";")
                        index = kategorie_split.index(jmeno_kategorie)
                        kategorie_split.pop(index)
                        kategorie_split.insert(index, kategorie_nova)
                        for x in kategorie_split:
                            if len(x) > 0: #tohle je je tady je z toho duvodu, ze pri splitu byly v seznamu i prazdne prvky, takze v bunce kategorie byly pak dalsi stredniky
                                kategorie_zapisku = kategorie_zapisku + unicode(x) + ";"
                        databaze.update("zapisky", where="cislo=$zapisek.cislo", kategorie=kategorie_zapisku, vars=locals())
                    databaze.update("kategorie", where="cislo=$cela_kategorie.cislo", cislo=cislo_nove, url_kategorie=url_kategorie_nova, popis=popis_novy, kategorie=kategorie_nova, vars=locals())
            except AttributeError:
                pass
            try:            
                if input.smaz:
                    cislo_kategorie = unicode(input.smaz)
                    cislo_kategorie = cislo_kategorie.split("_")[1]
                    databaze.delete("kategorie", where="cislo=$cislo_kategorie", vars=locals())
            except AttributeError:
                pass
            try:            
                if input.vloz:
                    cislo_nove = input.get("cislo_nove")
                    kategorie_nova = input.get("kategorie_nova")
                    url_kategorie_nova = input.get("url_kategorie_nova")
                    popis_novy = input.get("popis_novy")
                    databaze.insert("kategorie", cislo=cislo_nove, url_kategorie=url_kategorie_nova, popis=popis_novy, kategorie=kategorie_nova)
            except AttributeError:
                pass
            raise web.seeother("/admin/kategorie")
        else:
            return "Nemate dostatecne opravneni!!!"

class Komentare:
    """Trida pro administraci komentaru."""
    def GET(self):
        if Admin.session.get('logged_in', False):
            strankovani = web.input()
            cislo_strany = strankovani.strana if hasattr(strankovani, 'strana') else 1
            komentaru = 10
            offset = (int(cislo_strany) - 1) * komentaru
            seznam_komentaru = databaze.select("komentare", order="cislo_zapisku DESC", limit="$komentaru", offset="$offset", vars=locals())
            pocet = databaze.query("SELECT COUNT(*) AS komentaru FROM komentare")[0]
            stranky = pocet.komentaru / komentaru
            if pocet.komentaru % komentaru > 0:
                stranky += 1
            def ZISKEJ_URL(cislo):
                try:
                    url = ZISKEJ_ZAPISEK(int(cislo))["url"]
                    return url
                except TypeError:
                    return "KOMENTAR ZREJME NEPATRI K ZADNEMU ZAPISKU!!!"
            return sablona.komentare(seznam_komentaru, ZISKEJ_URL, stranky, cislo_strany)
        else:
            return "Nemate dostatecne opravneni!!!"

class Komentar_edituj:
    """Trida pro editaci jednoho komentare."""
    form_komentar_edit = web.form.Form(
    web.form.Textbox("nadpis_kom", web.form.notnull, size=50, description="Nadpis:"),
    web.form.Textbox("nick", web.form.notnull, size=50, description="Nick:"),
    web.form.Textarea("obsah", web.form.notnull, rows=8, cols=50, description="Obsah:"),
    web.form.Button("Upravit", value="Upravit"),
    ) # Formular pro editaci komentare
    def GET(self, cislo):
        if Admin.session.get('logged_in', False):
            komentar = ZISKEJ_KOMENTAR(cislo)
            form_komentar_edit = self.form_komentar_edit()
            form_komentar_edit.fill(komentar)
            if not komentar:
                return "Pozadovany komentar neexistuje."""
            return sablona.komentar(komentar, form_komentar_edit)
        else:
            return "Nemate dostatecne opravneni!!!"
    def POST(self, cislo):
        if Admin.session.get('logged_in', False):
            komentar = ZISKEJ_KOMENTAR(cislo)
            form_komentar_edit = self.form_komentar_edit()
            if not form_komentar_edit.validates():
                return sablona.komentar(komentar, form_komentar_edit)
            AKTUALIZUJ_KOMENTAR(int(cislo), form_komentar_edit.d.nadpis_kom, form_komentar_edit.d.nick, form_komentar_edit.d.obsah)

            raise web.seeother("/admin/komentare")
        else:
            return "Nemate dostatecne opravneni!!!"

class Komentar_smaz:
    """Trida pro zmazani jednoho komentare."""
    def GET(self, cislo):
        if Admin.session.get('logged_in', False):
            form_smaz = Smaz.form_smaz()
            return sablona.smaz(cislo, form_smaz)
        else:
            return "Nemate dostatecne opravneni!!!"
    def POST(self,cislo):
        if Admin.session.get('logged_in', False):
            form_smaz = Smaz.form_smaz()
            if not form_smaz.validates():
                return sablona.smaz(cislo, form_smaz)
            if form_smaz.d.Ano:
                komentar = ZISKEJ_KOMENTAR(cislo)
                zapisek = ZISKEJ_ZAPISEK(int(komentar.cislo_zapisku))
                SMAZ_KOMENTAR(unicode(cislo))
                zapisek.pocet_komentaru -= 1
                databaze.update("zapisky", where="cislo=$zapisek.cislo", vars=locals(), pocet_komentaru=zapisek.pocet_komentaru)
                raise web.seeother("/admin/komentare")
            if form_smaz.d.Ne:
                raise web.seeother("/admin/komentare")
        else:
            return "Nemate dostatecne opravneni!!!"

class Upload:
    def POST(self):
        if Admin.session.get('logged_in', False):
            x = web.input(file={})
            filedir = '/srv/http/virtual/jiri.one/soubory' # Adresar, kam se maji ukladat soubory
            if 'file' in x: # kontrola, jestli byl objekt souboru vytvoren
                filepath=x.file.filename.replace('\\','/') # nahradi windows lomitka za linuxova
                filename=filepath.split('/')[-1] # rozdeli celou cestu a necha jen posledni cast, tedy jmeno souboru s priponou
                fout = open(filedir +'/'+ filename,'w') # vytvori soubor v zadanem adresari
                fout.write(x.file.file.read()) # nahraje soubor do nove vytvoreneho souboru
                fout.close() # zavre otevreny soubor a je vyhrano :)
            return "/soubory/" + filename
        else:
            return "Nemate dostatecne opravneni!!!"

class Admin:
    """Trida pro administraci."""
    form_login = web.form.Form(
    web.form.Textbox("uzivatel", description="Jmeno: "),
    web.form.Password("heslo", description="Heslo: "),
    web.form.Button("Login")
    ) # Formular pro prihlaseni administratora

    seznam_kategorii = databaze.select("kategorie", order="cislo DESC")
    form_novy = web.form.Form() # Formular pro vytvoreni noveho zapisku
    for checkbox in seznam_kategorii:
        form_novy.inputs = (form_novy.inputs + ((web.form.Checkbox(unicode(checkbox.url_kategorie), value=unicode(checkbox.url_kategorie), description=unicode(checkbox.kategorie))),))
    form_novy.inputs = (form_novy.inputs + ((web.form.Textbox(u"nadpis_adm", web.form.notnull, size=40, description=u"Nadpis:</br>")),))
    form_novy.inputs = (form_novy.inputs + ((web.form.Textarea(u"obsah", web.form.notnull, rows=10, cols=80, description=u"Obsah:</br>")),))
    form_novy.inputs = (form_novy.inputs + ((web.form.Button(u"Odesli")),))

    store = web.session.DBStore(databaze, "sessions") # nastaveni, kam se maji ukladat sessions
    session = web.session.Session(app, store, initializer={"count": 0}) # samotne nastaveni sessions

    def GET(self):
        if self.session.get("logged_in", False): # pokud je nekdo prihlasen, udelej kod pod "if"
            #form_novy = self.form_novy()
            form_novy = vytvor_formular_administrace(self.form_novy())         
            strankovani = web.input()
            cislo_strany = strankovani.strana if hasattr(strankovani, 'strana') else 1
            zapisku = 20
            offset = (int(cislo_strany) - 1) * zapisku
            seznam_zapisku = databaze.select("zapisky", order="cislo DESC", limit="$zapisku", offset="$offset", vars=locals())
            pocet = databaze.query("SELECT COUNT(*) AS zapisku FROM zapisky")[0]
            stranky = pocet.zapisku / zapisku
            if pocet.zapisku % zapisku > 0:
                stranky += 1
            return sablona.admin(form_novy, seznam_zapisku, stranky, cislo_strany)
        else: # jinak pokud nekdo neni prihlasen, tak udelej kod pod "else"
            form_login = self.form_login()
            return sablona.login(form_login)

    def POST(self):
        if self.session.get("logged_in", False): # pokud je nekdo prihlasen, udelej kod pod "if"
            form_novy = self.form_novy()
            strankovani = web.input()
            cislo_strany = strankovani.strana if hasattr(strankovani, 'strana') else 1
            zapisku = 20
            offset = (int(cislo_strany) - 1) * zapisku
            seznam_zapisku = databaze.select("zapisky", order="cislo DESC", limit="$zapisku", offset="$offset", vars=locals())
            pocet = databaze.query("SELECT COUNT(*) AS zapisku FROM zapisky")[0]
            stranky = pocet.zapisku / zapisku
            if pocet.zapisku % zapisku > 0:
                stranky += 1
            if not form_novy.validates():
                return sablona.admin(form_novy, seznam_zapisku, stranky, cislo_strany)

            seznam_kategorii = databaze.select("kategorie", order="cislo DESC")
            kategorie_zapisku = unicode("")
            for kategorie in seznam_kategorii:
                checkbox = form_novy.get(kategorie.url_kategorie)
                if checkbox.get_value() == True:
                    kategorie_zapisku = kategorie_zapisku + unicode(kategorie.kategorie) + ";"
            cas = datetime.datetime.now()
            databaze.insert("zapisky", nadpis = form_novy.d.nadpis_adm, obsah = form_novy.d.obsah,
                            zadano_kdy=datetime.datetime.combine(cas.date(), datetime.time(cas.hour, cas.minute, cas.second)), url = remove_diacritic(form_novy.d.nadpis_adm),
                            kategorie = kategorie_zapisku)

            raise web.seeother("/admin")
        else: # jinak pokud nekdo neni prihlasen, tak udelej kod pod "else"
            try:
                form_login = self.form_login()
                if not form_login.validates():
                    return sablona.admin(form_login, seznam_zapisku, stranky, cislo_strany)
                uzivatel_zadano, heslo_zadano = form_login.d.uzivatel, form_login.d.heslo
                uzivatel_databaze = databaze.select("uzivatele", where="user=$uzivatel_zadano", vars=locals())[0]["user"]
                heslo_databaze = databaze.select("uzivatele", where="user=$uzivatel_zadano", vars=locals())[0]["pass"]
                if [uzivatel_zadano, heslo_zadano] == [uzivatel_databaze, heslo_databaze]:
                    self.session.logged_in = True
                    raise web.seeother("/admin")
            except:
                return "Spatne uzivatelske jmeno nebo heslo."


if __name__ == "__main__":
    app.run()
