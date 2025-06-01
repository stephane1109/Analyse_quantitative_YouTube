# cron_yt.py

from main import recuperer_cumul, enregistrer_cumul

if __name__ == "__main__":
    ligne = recuperer_cumul()
    if ligne:
        enregistrer_cumul(ligne)
        print("Enregistré :", ligne)
