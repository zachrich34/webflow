/**
 * WebFlow — frontend logic
 * All API communication uses the JWT stored in sessionStorage (NOT localStorage).
 * Keys never leave the server's memory.
 */

'use strict';

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

const state = {
  token: sessionStorage.getItem('wf_token') || null,
  username: sessionStorage.getItem('wf_user') || null,
  currentStep: 1,
  detectedBrowsers: [],
  sourceBrowser: null,
  sourceProfile: null,
  snapshotId: null,
  selectedDataTypes: new Set(['bookmarks', 'history']),
  destBrowser: null,
  destProfile: null,
  jobId: null,
  transferResult: null,
  // Subscription
  subscriptionTier: 'free',
  subscriptionFeatures: ['bookmarks', 'history'],
  paymentsEnabled: false,
};

// Free tier data types
// ---------------------------------------------------------------------------
// i18n
// ---------------------------------------------------------------------------

const TRANSLATIONS = {
  fr: {
    'upgrade-btn':'Upgrade ✨','manage-sub-btn':"Gérer l'abonnement",'logout-btn':'Déconnexion',
    'tab-login':'Login','tab-register':'Créer un compte','label-username':"Nom d'utilisateur",
    'label-password':'Mot de passe maître','label-email':'Email',
    'label-password-new':'Mot de passe maître (min. 8 car.)','remember-me':'Se souvenir de moi',
    'btn-continue':'Continuer →','btn-create-account':'Créer le compte →',
    'ph-username':'votre_pseudo','ph-strong-password':'Créez un mot de passe fort',
    'local-notice':'WebFlow tourne localement. Aucune donnée envoyée à des serveurs externes.',
    'step-account':'Compte','step-source':'Source','step-data':'Données',
    'step-dest':'Destination','step-transfer':'Transfert','step-done':'Terminé',
    'dash-subtitle':'Que voulez-vous faire aujourd\'hui ?',
    'dtab-new':'🚀 Nouveau transfert','dtab-transfers':'📋 Mes transferts',
    'dtab-plan':'💎 Mon plan','dtab-faq':'⭐ Review & FAQ',
    'hero-title':'Prêt à transférer ?',
    'hero-subtitle':'Déplacez vos bookmarks, historique, mots de passe et plus en quelques clics.',
    'btn-start-transfer':'🚀 Démarrer un transfert',
    'upcoming-section-title':'Fonctionnalités Pro & Premium',
    'upcoming-section-sub':'Cliquez pour en savoir plus — disponibles bientôt.',
    'upcoming-auto-name':'Transferts automatiques quotidiens','upcoming-auto-desc':'Sync automatique chaque jour — Premium',
    'upcoming-history-name':'Historique illimité','upcoming-history-desc':'Conservez tous vos transferts passés — Pro',
    'upcoming-multi-name':'Sync multi-profils','upcoming-multi-desc':'Gérez plusieurs profils simultanément — Premium',
    'upcoming-early-name':'Accès anticipé','upcoming-early-desc':'Nouvelles fonctionnalités en avant-première — Premium',
    'transfers-tab-title':'Historique des transferts',
    'transfers-tab-sub':"L'historique de vos transferts sera disponible ici très prochainement.",
    'transfers-tab-badge':'À venir — Pro & Premium','plan-tab-title':'Mon abonnement',
    'plan-compare-title':'Comparer les plans','faq-title':'Questions fréquentes',
    'review-title':'Donne ton avis sur la bêta',
    'review-sub':'2 minutes pour nous aider à améliorer WebFlow. Ton retour compte vraiment.',
    'review-btn':'✍️ Répondre au formulaire',
    'step2-back':'← Retour','step2-next':'Suivant →',
    'step3-back':'← Retour','step3-scan':'🔍 Scanner','step3-next':'Suivant →',
    'dt-bookmarks':'Bookmarks','dt-history':'Historique','dt-passwords':'Mots de passe',
    'dt-extensions':'Extensions','dt-settings':'Paramètres',
    'pro-section-label':'Pro & Premium — À venir',
    'pro-auto-name':'Transferts automatiques','pro-auto-desc':'Sync quotidienne programmée',
    'pro-history-name':'Historique illimité','pro-history-desc':'Tous vos transferts conservés',
    'pro-multi-name':'Multi-profils','pro-multi-desc':'Sync plusieurs profils en même temps',
    'pro-early-name':'Accès anticipé','pro-early-desc':'Nouvelles fonctionnalités en avant-première',
    'step4-back':'← Retour','step4-start':'🚀 Lancer le transfert',
    'step5-title':'Transfert en cours…','step5-sub':'Veuillez patienter. Ne fermez pas cette fenêtre.',
    'step6-title':'Transfert terminé !','step6-sub':'Vos données ont été transférées avec succès.',
    'btn-download':'📄 Télécharger le rapport','btn-new-transfer':'↺ Nouveau transfert',
    'footer':'WebFlow — outil local de transfert · Chiffrement AES-256 · Mots de passe jamais stockés en clair',
    'coming-soon-toast':'À venir pour Pro / Premium','welcome':'Bienvenue','logged-out':'Déconnecté.',
    'per-month':'/ mois','badge-popular':'Populaire','badge-best':'Meilleur','badge-current':'Actuel',
    'badge-free-btn':'Gratuit','feature-daily-sync':'Sync quotidienne','feature-early-access':'Accès anticipé',
    'sub-pro-btn':'Souscrire Pro →','sub-premium-btn':'Souscrire Premium →',
    'plan-current-label':'Plan actuel',
    'plan-msg-beta':'🧪 Accès bêta — toutes les fonctionnalités disponibles gratuitement.',
    'plan-msg-free':'Passez à Pro ou Premium pour accéder aux mots de passe, extensions et paramètres.',
    'plan-msg-pro':'⚡ Accès complet — sauf sync quotidienne et accès anticipé (Premium).',
    'plan-msg-premium':'👑 Vous avez accès à toutes les fonctionnalités.',
    'modal-upgrade-title':'Passer à la version supérieure',
    'modal-upgrade-sub':'Débloque le transfert de mots de passe, extensions et paramètres.',
    'payment-pending':'⏳ Paiement en cours dans ton navigateur…',
    'refresh-sub-btn':"Actualiser l'abonnement",'sub-updated':'Abonnement mis à jour :','error-prefix':'Erreur :',
    'review-q1':'Comment as-tu découvert WebFlow ?','review-q2':"Qu'est-ce qui a fonctionné ou pas ?",
    'review-q3':'Quelles fonctionnalités manquent ?',
    'review-q4':'Serais-tu prêt à payer pour WebFlow ? Si oui, combien/mois ?',
    'faq-q1':'Est-ce que mes données sont sécurisées ?',
    'faq-a1':'Oui. WebFlow fonctionne entièrement en local sur votre machine. Vos données sont chiffrées avec AES-256 et votre mot de passe maître ne quitte jamais votre appareil.',
    'faq-q2':'Quels navigateurs sont supportés ?',
    'faq-a2':'WebFlow supporte Chrome, Firefox, Opera GX, Microsoft Edge et Brave.',
    'faq-q3':'Les mots de passe sont-ils transférés directement ?',
    'faq-a3':'Les mots de passe sont exportés dans un fichier CSV dans le dossier de profil. Vous devez ensuite les importer manuellement via le gestionnaire de mots de passe du navigateur.',
    'faq-q4':'Puis-je transférer entre deux profils du même navigateur ?',
    'faq-a4':'Oui, vous pouvez transférer entre deux profils différents du même navigateur, mais pas vers le profil source identique.',
    'faq-q5':'Mes données sont-elles envoyées sur internet ?',
    'faq-a5':"Non. WebFlow tourne entièrement localement. Aucune donnée n'est envoyée à des serveurs externes. Votre compte est stocké localement.",
    'cs-title':'Les paiements arrivent bientôt !',
    'cs-body1':'WebFlow est actuellement en bêta gratuite — toutes les fonctionnalités sont disponibles sans abonnement. Les plans payants seront activés très prochainement.',
    'cs-body2':'En attendant, profite de tout gratuitement. 🎉','cs-btn':'Continuer gratuitement →',
  },
  en: {
    'upgrade-btn':'Upgrade ✨','manage-sub-btn':'Manage subscription','logout-btn':'Log out',
    'tab-login':'Login','tab-register':'Create account','label-username':'Username',
    'label-password':'Master password','label-email':'Email',
    'label-password-new':'Master password (min. 8 chars)','remember-me':'Remember me',
    'btn-continue':'Continue →','btn-create-account':'Create account →',
    'ph-username':'your_username','ph-strong-password':'Create a strong password',
    'local-notice':'WebFlow runs locally on your machine. No data is sent to external servers.',
    'step-account':'Account','step-source':'Source','step-data':'Data',
    'step-dest':'Destination','step-transfer':'Transfer','step-done':'Done',
    'dash-subtitle':'What would you like to do today?',
    'dtab-new':'🚀 New transfer','dtab-transfers':'📋 My transfers',
    'dtab-plan':'💎 My plan','dtab-faq':'⭐ Review & FAQ',
    'hero-title':'Ready to transfer?',
    'hero-subtitle':'Move your bookmarks, history, passwords and more in just a few clicks.',
    'btn-start-transfer':'🚀 Start a transfer',
    'upcoming-section-title':'Pro & Premium Features',
    'upcoming-section-sub':'Click to learn more — coming soon.',
    'upcoming-auto-name':'Automatic daily transfers','upcoming-auto-desc':'Automatic sync every day — Premium',
    'upcoming-history-name':'Unlimited history','upcoming-history-desc':'Keep all your past transfers — Pro',
    'upcoming-multi-name':'Multi-profile sync','upcoming-multi-desc':'Manage multiple profiles at once — Premium',
    'upcoming-early-name':'Early access','upcoming-early-desc':'New features first — Premium',
    'transfers-tab-title':'Transfer history',
    'transfers-tab-sub':'Your transfer history will be available here very soon.',
    'transfers-tab-badge':'Coming soon — Pro & Premium','plan-tab-title':'My subscription',
    'plan-compare-title':'Compare plans','faq-title':'Frequently asked questions',
    'review-title':'Share your beta feedback',
    'review-sub':'2 minutes to help us improve WebFlow. Your feedback really matters.',
    'review-btn':'✍️ Fill out the form',
    'step2-back':'← Back','step2-next':'Next →',
    'step3-back':'← Back','step3-scan':'🔍 Scan browser','step3-next':'Next →',
    'dt-bookmarks':'Bookmarks','dt-history':'History','dt-passwords':'Passwords',
    'dt-extensions':'Extensions','dt-settings':'Settings',
    'pro-section-label':'Pro & Premium — Coming soon',
    'pro-auto-name':'Automatic transfers','pro-auto-desc':'Scheduled daily sync',
    'pro-history-name':'Unlimited history','pro-history-desc':'All your transfers saved',
    'pro-multi-name':'Multi-profile','pro-multi-desc':'Sync multiple profiles at once',
    'pro-early-name':'Early access','pro-early-desc':'New features first',
    'step4-back':'← Back','step4-start':'🚀 Start transfer',
    'step5-title':'Transferring your data…','step5-sub':'Please wait. Do not close this window.',
    'step6-title':'Transfer complete!','step6-sub':'Your browser data has been successfully transferred.',
    'btn-download':'📄 Download report','btn-new-transfer':'↺ New transfer',
    'footer':'WebFlow — local browser data transfer tool · All data encrypted with AES-256 · Passwords never stored in plaintext',
    'coming-soon-toast':'Coming soon for Pro / Premium','welcome':'Welcome','logged-out':'Logged out.',
    'per-month':'/ month','badge-popular':'Popular','badge-best':'Best','badge-current':'Current',
    'badge-free-btn':'Free','feature-daily-sync':'Daily sync','feature-early-access':'Early access',
    'sub-pro-btn':'Subscribe Pro →','sub-premium-btn':'Subscribe Premium →',
    'plan-current-label':'Current plan',
    'plan-msg-beta':'🧪 Beta access — all features available for free.',
    'plan-msg-free':'Upgrade to Pro or Premium to access passwords, extensions and settings.',
    'plan-msg-pro':'⚡ Full access — except daily sync and early access (Premium).',
    'plan-msg-premium':'👑 You have access to all features.',
    'modal-upgrade-title':'Upgrade your plan',
    'modal-upgrade-sub':'Unlock password, extension and settings transfer.',
    'payment-pending':'⏳ Payment in progress in your browser…',
    'refresh-sub-btn':'Refresh subscription','sub-updated':'Subscription updated:','error-prefix':'Error:',
    'review-q1':'How did you discover WebFlow?','review-q2':'What worked or didn\'t work?',
    'review-q3':'What features are missing?',
    'review-q4':'Would you pay for WebFlow? If so, how much/month?',
    'faq-q1':'Is my data secure?',
    'faq-a1':'Yes. WebFlow runs entirely locally on your machine. Your data is encrypted with AES-256 and your master password never leaves your device.',
    'faq-q2':'Which browsers are supported?',
    'faq-a2':'WebFlow supports Chrome, Firefox, Opera GX, Microsoft Edge and Brave.',
    'faq-q3':'Are passwords transferred directly?',
    'faq-a3':'Passwords are exported to a CSV file in the destination browser\'s profile folder. You then need to import them manually via the browser\'s password manager.',
    'faq-q4':'Can I transfer between profiles of the same browser?',
    'faq-a4':'Yes, you can transfer between two different profiles of the same browser, but not to the same source profile.',
    'faq-q5':'Is my data sent to the internet?',
    'faq-a5':'No. WebFlow runs entirely locally. No data is sent to external servers. Your account is stored locally on your machine.',
    'cs-title':'Payments coming soon!',
    'cs-body1':'WebFlow is currently in free beta — all features are available without a subscription. Paid plans will be activated very soon.',
    'cs-body2':'In the meantime, enjoy everything for free. 🎉','cs-btn':'Continue for free →',
  },
  de: {
    'upgrade-btn':'Upgrade ✨','manage-sub-btn':'Abo verwalten','logout-btn':'Abmelden',
    'tab-login':'Anmelden','tab-register':'Konto erstellen','label-username':'Benutzername',
    'label-password':'Master-Passwort','label-email':'E-Mail',
    'label-password-new':'Master-Passwort (min. 8 Zeichen)','remember-me':'Angemeldet bleiben',
    'btn-continue':'Weiter →','btn-create-account':'Konto erstellen →',
    'ph-username':'dein_benutzername','ph-strong-password':'Sicheres Passwort erstellen',
    'local-notice':'WebFlow läuft lokal. Keine Daten werden an externe Server gesendet.',
    'step-account':'Konto','step-source':'Quelle','step-data':'Daten',
    'step-dest':'Ziel','step-transfer':'Transfer','step-done':'Fertig',
    'dash-subtitle':'Was möchten Sie heute tun?',
    'dtab-new':'🚀 Neuer Transfer','dtab-transfers':'📋 Meine Transfers',
    'dtab-plan':'💎 Mein Plan','dtab-faq':'⭐ Bewertung & FAQ',
    'hero-title':'Bereit zum Übertragen?',
    'hero-subtitle':'Verschieben Sie Lesezeichen, Verlauf und Passwörter in wenigen Klicks.',
    'btn-start-transfer':'🚀 Transfer starten',
    'upcoming-section-title':'Pro & Premium Funktionen',
    'upcoming-section-sub':'Klicken für mehr Infos — bald verfügbar.',
    'upcoming-auto-name':'Automatische tägliche Transfers','upcoming-auto-desc':'Tägliche Synchronisierung — Premium',
    'upcoming-history-name':'Unbegrenzter Verlauf','upcoming-history-desc':'Alle Transfers speichern — Pro',
    'upcoming-multi-name':'Multi-Profil-Sync','upcoming-multi-desc':'Mehrere Profile gleichzeitig — Premium',
    'upcoming-early-name':'Früher Zugang','upcoming-early-desc':'Neue Funktionen zuerst — Premium',
    'transfers-tab-title':'Transferverlauf',
    'transfers-tab-sub':'Ihr Transferverlauf wird hier bald verfügbar sein.',
    'transfers-tab-badge':'Demnächst — Pro & Premium','plan-tab-title':'Mein Abonnement',
    'plan-compare-title':'Pläne vergleichen','faq-title':'Häufig gestellte Fragen',
    'review-title':'Beta-Feedback geben',
    'review-sub':'2 Minuten, um uns zu helfen WebFlow zu verbessern.',
    'review-btn':'✍️ Formular ausfüllen',
    'step2-back':'← Zurück','step2-next':'Weiter →',
    'step3-back':'← Zurück','step3-scan':'🔍 Browser scannen','step3-next':'Weiter →',
    'dt-bookmarks':'Lesezeichen','dt-history':'Verlauf','dt-passwords':'Passwörter',
    'dt-extensions':'Erweiterungen','dt-settings':'Einstellungen',
    'pro-section-label':'Pro & Premium — Demnächst',
    'pro-auto-name':'Automatische Transfers','pro-auto-desc':'Geplante tägliche Synchronisierung',
    'pro-history-name':'Unbegrenzter Verlauf','pro-history-desc':'Alle Transfers gespeichert',
    'pro-multi-name':'Multi-Profil','pro-multi-desc':'Mehrere Profile gleichzeitig',
    'pro-early-name':'Früher Zugang','pro-early-desc':'Neue Funktionen zuerst',
    'step4-back':'← Zurück','step4-start':'🚀 Transfer starten',
    'step5-title':'Daten werden übertragen…','step5-sub':'Bitte warten. Fenster nicht schließen.',
    'step6-title':'Transfer abgeschlossen!','step6-sub':'Ihre Browserdaten wurden erfolgreich übertragen.',
    'btn-download':'📄 Bericht herunterladen','btn-new-transfer':'↺ Neuer Transfer',
    'footer':'WebFlow — lokales Transfer-Tool · AES-256-Verschlüsselung',
    'coming-soon-toast':'Demnächst für Pro / Premium','welcome':'Willkommen','logged-out':'Abgemeldet.',
    'per-month':'/ Monat','badge-popular':'Beliebt','badge-best':'Bestes','badge-current':'Aktuell',
    'badge-free-btn':'Kostenlos','feature-daily-sync':'Tägliche Sync','feature-early-access':'Früher Zugang',
    'sub-pro-btn':'Pro abonnieren →','sub-premium-btn':'Premium abonnieren →',
    'plan-current-label':'Aktueller Plan',
    'plan-msg-beta':'🧪 Beta-Zugang — alle Funktionen kostenlos verfügbar.',
    'plan-msg-free':'Upgraden Sie auf Pro oder Premium für Passwörter, Erweiterungen und Einstellungen.',
    'plan-msg-pro':'⚡ Vollzugang — außer täglicher Sync und frühem Zugang (Premium).',
    'plan-msg-premium':'👑 Sie haben Zugang zu allen Funktionen.',
    'modal-upgrade-title':'Plan upgraden',
    'modal-upgrade-sub':'Schaltet Passwort-, Erweiterungs- und Einstellungsübertragung frei.',
    'payment-pending':'⏳ Zahlung läuft in Ihrem Browser…',
    'refresh-sub-btn':'Abonnement aktualisieren','sub-updated':'Abonnement aktualisiert:','error-prefix':'Fehler:',
    'review-q1':'Wie haben Sie WebFlow entdeckt?','review-q2':'Was hat funktioniert oder nicht?',
    'review-q3':'Welche Funktionen fehlen?',
    'review-q4':'Würden Sie für WebFlow zahlen? Wenn ja, wie viel/Monat?',
    'faq-q1':'Sind meine Daten sicher?',
    'faq-a1':'Ja. WebFlow läuft vollständig lokal. Ihre Daten werden mit AES-256 verschlüsselt und Ihr Master-Passwort verlässt nie Ihr Gerät.',
    'faq-q2':'Welche Browser werden unterstützt?',
    'faq-a2':'WebFlow unterstützt Chrome, Firefox, Opera GX, Microsoft Edge und Brave.',
    'faq-q3':'Werden Passwörter direkt übertragen?',
    'faq-a3':'Passwörter werden in eine CSV-Datei exportiert. Sie müssen diese dann manuell über den Passwort-Manager des Browsers importieren.',
    'faq-q4':'Kann ich zwischen Profilen desselben Browsers übertragen?',
    'faq-a4':'Ja, zwischen zwei verschiedenen Profilen desselben Browsers, aber nicht zum gleichen Quellprofil.',
    'faq-q5':'Werden meine Daten ins Internet gesendet?',
    'faq-a5':'Nein. WebFlow läuft vollständig lokal. Es werden keine Daten an externe Server gesendet.',
    'cs-title':'Zahlungen kommen bald!',
    'cs-body1':'WebFlow befindet sich derzeit in der kostenlosen Beta — alle Funktionen sind ohne Abonnement verfügbar. Bezahlpläne werden sehr bald aktiviert.',
    'cs-body2':'In der Zwischenzeit alles kostenlos nutzen. 🎉','cs-btn':'Kostenlos weitermachen →',
  },
  ru: {
    'upgrade-btn':'Улучшить ✨','manage-sub-btn':'Управление подпиской','logout-btn':'Выйти',
    'tab-login':'Войти','tab-register':'Создать аккаунт','label-username':'Имя пользователя',
    'label-password':'Мастер-пароль','label-email':'Email',
    'label-password-new':'Мастер-пароль (мин. 8 симв.)','remember-me':'Запомнить меня',
    'btn-continue':'Продолжить →','btn-create-account':'Создать аккаунт →',
    'ph-username':'ваш_ник','ph-strong-password':'Создайте надёжный пароль',
    'local-notice':'WebFlow работает локально. Данные не отправляются на внешние серверы.',
    'step-account':'Аккаунт','step-source':'Источник','step-data':'Данные',
    'step-dest':'Назначение','step-transfer':'Перенос','step-done':'Готово',
    'dash-subtitle':'Что вы хотите сделать сегодня?',
    'dtab-new':'🚀 Новый перенос','dtab-transfers':'📋 Мои переносы',
    'dtab-plan':'💎 Мой план','dtab-faq':'⭐ Отзыв & FAQ',
    'hero-title':'Готовы к переносу?',
    'hero-subtitle':'Перенесите закладки, историю, пароли и многое другое за несколько кликов.',
    'btn-start-transfer':'🚀 Начать перенос',
    'upcoming-section-title':'Функции Pro и Premium',
    'upcoming-section-sub':'Нажмите для подробностей — скоро будет доступно.',
    'upcoming-auto-name':'Автоматические ежедневные переносы','upcoming-auto-desc':'Автоматическая синхронизация — Premium',
    'upcoming-history-name':'Безлимитная история','upcoming-history-desc':'Все прошлые переносы — Pro',
    'upcoming-multi-name':'Мультипрофильная синхронизация','upcoming-multi-desc':'Управление несколькими профилями — Premium',
    'upcoming-early-name':'Ранний доступ','upcoming-early-desc':'Новые функции первыми — Premium',
    'transfers-tab-title':'История переносов',
    'transfers-tab-sub':'История ваших переносов скоро появится здесь.',
    'transfers-tab-badge':'Скоро — Pro и Premium','plan-tab-title':'Моя подписка',
    'plan-compare-title':'Сравнить планы','faq-title':'Часто задаваемые вопросы',
    'review-title':'Оставьте отзыв о бете',
    'review-sub':'2 минуты, чтобы помочь нам улучшить WebFlow.',
    'review-btn':'✍️ Заполнить форму',
    'step2-back':'← Назад','step2-next':'Далее →',
    'step3-back':'← Назад','step3-scan':'🔍 Сканировать','step3-next':'Далее →',
    'dt-bookmarks':'Закладки','dt-history':'История','dt-passwords':'Пароли',
    'dt-extensions':'Расширения','dt-settings':'Настройки',
    'pro-section-label':'Pro и Premium — Скоро',
    'pro-auto-name':'Автоматические переносы','pro-auto-desc':'Ежедневная синхронизация',
    'pro-history-name':'Безлимитная история','pro-history-desc':'Все переносы сохранены',
    'pro-multi-name':'Мультипрофиль','pro-multi-desc':'Несколько профилей одновременно',
    'pro-early-name':'Ранний доступ','pro-early-desc':'Новые функции первыми',
    'step4-back':'← Назад','step4-start':'🚀 Начать перенос',
    'step5-title':'Перенос данных…','step5-sub':'Пожалуйста, подождите. Не закрывайте окно.',
    'step6-title':'Перенос завершён!','step6-sub':'Данные браузера успешно перенесены.',
    'btn-download':'📄 Скачать отчёт','btn-new-transfer':'↺ Новый перенос',
    'footer':'WebFlow — локальный инструмент переноса · Шифрование AES-256',
    'coming-soon-toast':'Скоро для Pro / Premium','welcome':'Добро пожаловать','logged-out':'Вы вышли.',
    'per-month':'/ мес','badge-popular':'Популярное','badge-best':'Лучшее','badge-current':'Текущий',
    'badge-free-btn':'Бесплатно','feature-daily-sync':'Ежедневная синхр.','feature-early-access':'Ранний доступ',
    'sub-pro-btn':'Подписаться Pro →','sub-premium-btn':'Подписаться Premium →',
    'plan-current-label':'Текущий план',
    'plan-msg-beta':'🧪 Бета-доступ — все функции доступны бесплатно.',
    'plan-msg-free':'Перейдите на Pro или Premium для доступа к паролям, расширениям и настройкам.',
    'plan-msg-pro':'⚡ Полный доступ — кроме ежедневной синхронизации и раннего доступа (Premium).',
    'plan-msg-premium':'👑 У вас есть доступ ко всем функциям.',
    'modal-upgrade-title':'Улучшить план',
    'modal-upgrade-sub':'Открывает перенос паролей, расширений и настроек.',
    'payment-pending':'⏳ Оплата выполняется в вашем браузере…',
    'refresh-sub-btn':'Обновить подписку','sub-updated':'Подписка обновлена:','error-prefix':'Ошибка:',
    'review-q1':'Как вы узнали о WebFlow?','review-q2':'Что сработало или нет?',
    'review-q3':'Каких функций не хватает?',
    'review-q4':'Готовы ли вы платить за WebFlow? Если да, сколько/месяц?',
    'faq-q1':'Мои данные в безопасности?',
    'faq-a1':'Да. WebFlow работает полностью локально. Данные зашифрованы AES-256, мастер-пароль никогда не покидает устройство.',
    'faq-q2':'Какие браузеры поддерживаются?',
    'faq-a2':'WebFlow поддерживает Chrome, Firefox, Opera GX, Microsoft Edge и Brave.',
    'faq-q3':'Пароли переносятся напрямую?',
    'faq-a3':'Пароли экспортируются в CSV-файл. Затем нужно импортировать их через менеджер паролей браузера.',
    'faq-q4':'Можно переносить между профилями одного браузера?',
    'faq-a4':'Да, между двумя разными профилями одного браузера, но не в тот же исходный профиль.',
    'faq-q5':'Данные отправляются в интернет?',
    'faq-a5':'Нет. WebFlow работает полностью локально. Никакие данные не отправляются на внешние серверы.',
    'cs-title':'Платежи скоро появятся!',
    'cs-body1':'WebFlow сейчас в бесплатной бете — все функции доступны без подписки. Платные планы будут активированы очень скоро.',
    'cs-body2':'А пока пользуйтесь всем бесплатно. 🎉','cs-btn':'Продолжить бесплатно →',
  },
  tr: {
    'upgrade-btn':'Yükselt ✨','manage-sub-btn':'Aboneliği yönet','logout-btn':'Çıkış yap',
    'tab-login':'Giriş yap','tab-register':'Hesap oluştur','label-username':'Kullanıcı adı',
    'label-password':'Ana şifre','label-email':'E-posta',
    'label-password-new':'Ana şifre (min. 8 karakter)','remember-me':'Beni hatırla',
    'btn-continue':'Devam et →','btn-create-account':'Hesap oluştur →',
    'ph-username':'kullanici_adi','ph-strong-password':'Güçlü bir şifre oluşturun',
    'local-notice':'WebFlow yerel olarak çalışır. Hiçbir veri harici sunuculara gönderilmez.',
    'step-account':'Hesap','step-source':'Kaynak','step-data':'Veri',
    'step-dest':'Hedef','step-transfer':'Transfer','step-done':'Tamam',
    'dash-subtitle':'Bugün ne yapmak istersiniz?',
    'dtab-new':'🚀 Yeni transfer','dtab-transfers':'📋 Transferlerim',
    'dtab-plan':'💎 Planım','dtab-faq':'⭐ İnceleme & SSS',
    'hero-title':'Transfere hazır mısınız?',
    'hero-subtitle':'Yer işaretlerinizi, geçmişinizi ve şifrelerinizi birkaç tıkla taşıyın.',
    'btn-start-transfer':'🚀 Transfer başlat',
    'upcoming-section-title':'Pro ve Premium Özellikler',
    'upcoming-section-sub':'Daha fazla bilgi için tıklayın — yakında geliyor.',
    'upcoming-auto-name':'Otomatik günlük transferler','upcoming-auto-desc':'Her gün otomatik senkronizasyon — Premium',
    'upcoming-history-name':'Sınırsız geçmiş','upcoming-history-desc':'Tüm geçmiş transferleriniz — Pro',
    'upcoming-multi-name':'Çoklu profil sync','upcoming-multi-desc':'Birden fazla profili yönetin — Premium',
    'upcoming-early-name':'Erken erişim','upcoming-early-desc':'Yeni özellikler ilk sizde — Premium',
    'transfers-tab-title':'Transfer geçmişi',
    'transfers-tab-sub':'Transfer geçmişiniz çok yakında burada olacak.',
    'transfers-tab-badge':'Yakında — Pro ve Premium','plan-tab-title':'Aboneliğim',
    'plan-compare-title':'Planları karşılaştır','faq-title':'Sık sorulan sorular',
    'review-title':'Beta geri bildiriminizi paylaşın',
    'review-sub':"WebFlow'u geliştirmemize yardımcı olmak için 2 dakika.",
    'review-btn':'✍️ Formu doldur',
    'step2-back':'← Geri','step2-next':'İleri →',
    'step3-back':'← Geri','step3-scan':'🔍 Tara','step3-next':'İleri →',
    'dt-bookmarks':'Yer işaretleri','dt-history':'Geçmiş','dt-passwords':'Şifreler',
    'dt-extensions':'Uzantılar','dt-settings':'Ayarlar',
    'pro-section-label':'Pro ve Premium — Yakında',
    'pro-auto-name':'Otomatik transferler','pro-auto-desc':'Planlanmış günlük senkronizasyon',
    'pro-history-name':'Sınırsız geçmiş','pro-history-desc':'Tüm transferleriniz kaydedildi',
    'pro-multi-name':'Çoklu profil','pro-multi-desc':'Birden fazla profili aynı anda',
    'pro-early-name':'Erken erişim','pro-early-desc':'Yeni özellikler ilk sizde',
    'step4-back':'← Geri','step4-start':'🚀 Transferi başlat',
    'step5-title':'Veriler aktarılıyor…','step5-sub':'Lütfen bekleyin. Bu pencereyi kapatmayın.',
    'step6-title':'Transfer tamamlandı!','step6-sub':'Tarayıcı verileriniz başarıyla aktarıldı.',
    'btn-download':'📄 Raporu indir','btn-new-transfer':'↺ Yeni transfer',
    'footer':'WebFlow — yerel tarayıcı veri aktarım aracı · AES-256 şifreleme',
    'coming-soon-toast':'Pro / Premium için yakında','welcome':'Hoş geldiniz','logged-out':'Çıkış yapıldı.',
    'per-month':'/ ay','badge-popular':'Popüler','badge-best':'En iyi','badge-current':'Mevcut',
    'badge-free-btn':'Ücretsiz','feature-daily-sync':'Günlük senkronizasyon','feature-early-access':'Erken erişim',
    'sub-pro-btn':"Pro'ya abone ol →",'sub-premium-btn':"Premium'a abone ol →",
    'plan-current-label':'Mevcut plan',
    'plan-msg-beta':'🧪 Beta erişimi — tüm özellikler ücretsiz.',
    'plan-msg-free':"Şifreler, uzantılar ve ayarlara erişmek için Pro veya Premium'a geçin.",
    'plan-msg-pro':'⚡ Tam erişim — günlük senkronizasyon ve erken erişim hariç (Premium).',
    'plan-msg-premium':'👑 Tüm özelliklere erişiminiz var.',
    'modal-upgrade-title':'Planınızı yükseltin',
    'modal-upgrade-sub':'Şifre, uzantı ve ayar transferini açar.',
    'payment-pending':'⏳ Ödeme tarayıcınızda devam ediyor…',
    'refresh-sub-btn':'Aboneliği yenile','sub-updated':'Abonelik güncellendi:','error-prefix':'Hata:',
    'review-q1':"WebFlow'u nasıl keşfettiniz?",'review-q2':'Ne işe yaradı ya da yaramadı?',
    'review-q3':'Hangi özellikler eksik?',
    'review-q4':'WebFlow için ödeme yapar mıydınız? Evet ise ne kadar/ay?',
    'faq-q1':'Verilerim güvende mi?',
    'faq-a1':'Evet. WebFlow tamamen yerel olarak çalışır. Veriler AES-256 ile şifrelenir, ana şifre cihazı asla terk etmez.',
    'faq-q2':'Hangi tarayıcılar destekleniyor?',
    'faq-a2':'WebFlow; Chrome, Firefox, Opera GX, Microsoft Edge ve Brave\'i destekler.',
    'faq-q3':'Şifreler doğrudan aktarılıyor mu?',
    'faq-a3':'Şifreler CSV dosyasına aktarılır. Ardından tarayıcının şifre yöneticisi aracılığıyla manuel olarak içe aktarmanız gerekir.',
    'faq-q4':'Aynı tarayıcının profilleri arasında aktarım yapabilir miyim?',
    'faq-a4':'Evet, aynı tarayıcının iki farklı profili arasında, ancak kaynak profille aynı olamaz.',
    'faq-q5':'Verilerim internete gönderiliyor mu?',
    'faq-a5':'Hayır. WebFlow tamamen yerel olarak çalışır. Hiçbir veri harici sunuculara gönderilmez.',
    'cs-title':'Ödemeler yakında geliyor!',
    'cs-body1':'WebFlow şu anda ücretsiz betada — tüm özellikler abonelik olmadan kullanılabilir. Ücretli planlar çok yakında etkinleştirilecek.',
    'cs-body2':'Bu arada her şeyi ücretsiz kullanın. 🎉','cs-btn':'Ücretsiz devam et →',
  },
  es: {
    'upgrade-btn':'Mejorar ✨','manage-sub-btn':'Gestionar suscripción','logout-btn':'Cerrar sesión',
    'tab-login':'Iniciar sesión','tab-register':'Crear cuenta','label-username':'Usuario',
    'label-password':'Contraseña maestra','label-email':'Correo electrónico',
    'label-password-new':'Contraseña maestra (mín. 8 car.)','remember-me':'Recuérdame',
    'btn-continue':'Continuar →','btn-create-account':'Crear cuenta →',
    'ph-username':'tu_usuario','ph-strong-password':'Crea una contraseña segura',
    'local-notice':'WebFlow se ejecuta localmente. No se envían datos a servidores externos.',
    'step-account':'Cuenta','step-source':'Origen','step-data':'Datos',
    'step-dest':'Destino','step-transfer':'Transferencia','step-done':'Hecho',
    'dash-subtitle':'¿Qué quieres hacer hoy?',
    'dtab-new':'🚀 Nueva transferencia','dtab-transfers':'📋 Mis transferencias',
    'dtab-plan':'💎 Mi plan','dtab-faq':'⭐ Reseña & FAQ',
    'hero-title':'¿Listo para transferir?',
    'hero-subtitle':'Mueve tus marcadores, historial y contraseñas en pocos clics.',
    'btn-start-transfer':'🚀 Iniciar transferencia',
    'upcoming-section-title':'Funciones Pro y Premium',
    'upcoming-section-sub':'Haz clic para más info — próximamente.',
    'upcoming-auto-name':'Transferencias automáticas diarias','upcoming-auto-desc':'Sincronización automática cada día — Premium',
    'upcoming-history-name':'Historial ilimitado','upcoming-history-desc':'Guarda todas tus transferencias — Pro',
    'upcoming-multi-name':'Sincronización multi-perfil','upcoming-multi-desc':'Gestiona varios perfiles a la vez — Premium',
    'upcoming-early-name':'Acceso anticipado','upcoming-early-desc':'Nuevas funciones primero — Premium',
    'transfers-tab-title':'Historial de transferencias',
    'transfers-tab-sub':'Tu historial de transferencias estará disponible muy pronto.',
    'transfers-tab-badge':'Próximamente — Pro y Premium','plan-tab-title':'Mi suscripción',
    'plan-compare-title':'Comparar planes','faq-title':'Preguntas frecuentes',
    'review-title':'Comparte tu opinión sobre la beta',
    'review-sub':'2 minutos para ayudarnos a mejorar WebFlow.',
    'review-btn':'✍️ Rellenar el formulario',
    'step2-back':'← Atrás','step2-next':'Siguiente →',
    'step3-back':'← Atrás','step3-scan':'🔍 Escanear','step3-next':'Siguiente →',
    'dt-bookmarks':'Marcadores','dt-history':'Historial','dt-passwords':'Contraseñas',
    'dt-extensions':'Extensiones','dt-settings':'Configuración',
    'pro-section-label':'Pro y Premium — Próximamente',
    'pro-auto-name':'Transferencias automáticas','pro-auto-desc':'Sincronización diaria programada',
    'pro-history-name':'Historial ilimitado','pro-history-desc':'Todas tus transferencias guardadas',
    'pro-multi-name':'Multi-perfil','pro-multi-desc':'Varios perfiles a la vez',
    'pro-early-name':'Acceso anticipado','pro-early-desc':'Nuevas funciones primero',
    'step4-back':'← Atrás','step4-start':'🚀 Iniciar transferencia',
    'step5-title':'Transfiriendo datos…','step5-sub':'Por favor espera. No cierres esta ventana.',
    'step6-title':'¡Transferencia completa!','step6-sub':'Los datos de tu navegador se han transferido con éxito.',
    'btn-download':'📄 Descargar informe','btn-new-transfer':'↺ Nueva transferencia',
    'footer':'WebFlow — herramienta local de transferencia · Cifrado AES-256',
    'coming-soon-toast':'Próximamente para Pro / Premium','welcome':'Bienvenido','logged-out':'Sesión cerrada.',
    'per-month':'/ mes','badge-popular':'Popular','badge-best':'Mejor','badge-current':'Actual',
    'badge-free-btn':'Gratis','feature-daily-sync':'Sincronización diaria','feature-early-access':'Acceso anticipado',
    'sub-pro-btn':'Suscribirse Pro →','sub-premium-btn':'Suscribirse Premium →',
    'plan-current-label':'Plan actual',
    'plan-msg-beta':'🧪 Acceso beta — todas las funciones disponibles gratuitamente.',
    'plan-msg-free':'Actualiza a Pro o Premium para acceder a contraseñas, extensiones y configuración.',
    'plan-msg-pro':'⚡ Acceso completo — excepto sincronización diaria y acceso anticipado (Premium).',
    'plan-msg-premium':'👑 Tienes acceso a todas las funciones.',
    'modal-upgrade-title':'Mejorar tu plan',
    'modal-upgrade-sub':'Desbloquea la transferencia de contraseñas, extensiones y configuración.',
    'payment-pending':'⏳ Pago en curso en tu navegador…',
    'refresh-sub-btn':'Actualizar suscripción','sub-updated':'Suscripción actualizada:','error-prefix':'Error:',
    'review-q1':'¿Cómo descubriste WebFlow?','review-q2':'¿Qué funcionó o no funcionó?',
    'review-q3':'¿Qué funciones faltan?',
    'review-q4':'¿Pagarías por WebFlow? Si es así, ¿cuánto/mes?',
    'faq-q1':'¿Están seguros mis datos?',
    'faq-a1':'Sí. WebFlow funciona completamente de forma local. Tus datos están cifrados con AES-256 y tu contraseña maestra nunca sale de tu dispositivo.',
    'faq-q2':'¿Qué navegadores son compatibles?',
    'faq-a2':'WebFlow es compatible con Chrome, Firefox, Opera GX, Microsoft Edge y Brave.',
    'faq-q3':'¿Las contraseñas se transfieren directamente?',
    'faq-a3':'Las contraseñas se exportan a un archivo CSV. Luego debes importarlas manualmente a través del gestor de contraseñas del navegador.',
    'faq-q4':'¿Puedo transferir entre perfiles del mismo navegador?',
    'faq-a4':'Sí, entre dos perfiles diferentes del mismo navegador, pero no al mismo perfil de origen.',
    'faq-q5':'¿Mis datos se envían a internet?',
    'faq-a5':'No. WebFlow funciona completamente de forma local. No se envían datos a servidores externos.',
    'cs-title':'¡Los pagos llegan pronto!',
    'cs-body1':'WebFlow está actualmente en beta gratuita — todas las funciones están disponibles sin suscripción. Los planes de pago se activarán muy pronto.',
    'cs-body2':'Mientras tanto, disfruta de todo gratis. 🎉','cs-btn':'Continuar gratis →',
  },
};

function t(key) {
  const lang = state.lang || 'fr';
  return (TRANSLATIONS[lang] && TRANSLATIONS[lang][key]) || (TRANSLATIONS.fr[key]) || key;
}

function setLanguage(lang) {
  state.lang = lang;
  localStorage.setItem('wf_lang', lang);
  const sel = document.getElementById('langSelect');
  if (sel) sel.value = lang;
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const val = t(el.dataset.i18n);
    if (val) el.textContent = val;
  });
  document.querySelectorAll('[data-i18n-ph]').forEach(el => {
    const val = t(el.dataset.i18nPh);
    if (val) el.placeholder = val;
  });
  // Re-render dynamic sections that use t()
  updatePlanDetails();
}

function loadLanguage() {
  const saved = localStorage.getItem('wf_lang') || 'fr';
  state.lang = saved;
  setLanguage(saved);
}

// Free tier data types
const FREE_TYPES = new Set(['bookmarks', 'history']);
// Pro/Premium data types
const PRO_TYPES  = new Set(['bookmarks', 'history', 'passwords', 'extensions', 'settings']);

// Browser display info
const BROWSER_INFO = {
  chrome:    { emoji: '🌐', label: 'Google Chrome',   color: '#4285F4' },
  firefox:   { emoji: '🦊', label: 'Mozilla Firefox', color: '#FF7139' },
  opera_gx:  { emoji: '🎮', label: 'Opera GX',        color: '#FF1B2D' },
  edge:      { emoji: '🔷', label: 'Microsoft Edge',   color: '#0078D7' },
  brave:     { emoji: '🦁', label: 'Brave',            color: '#FB542B' },
};

const DATA_TYPE_EMOJI = {
  bookmarks: '🔖',
  history: '📅',
  passwords: '🔑',
  extensions: '🧩',
  settings: '⚙️',
};

// ---------------------------------------------------------------------------
// Bootstrap
// ---------------------------------------------------------------------------

document.addEventListener('DOMContentLoaded', () => {
  loadLanguage();
  // Try auto-login from saved credentials
  const saved = loadRemembered();
  if (saved) {
    autoLogin(saved.username, saved.password);
    return;
  }

  if (state.token) {
    verifyToken().then(ok => {
      if (ok) {
        updateHeaderUI();
        loadSubscriptionStatus().then(() => showDash());
      } else {
        clearAuth();
      }
    });
  }

  // Allow Enter key on auth inputs
  ['loginUsername','loginPassword','regUsername','regEmail','regPassword'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener('keydown', e => { if (e.key === 'Enter') e.target.closest('.card').querySelector('.btn-primary').click(); });
  });
});

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------

async function api(method, path, body = null) {
  const headers = { 'Content-Type': 'application/json' };
  if (state.token) headers['Authorization'] = `Bearer ${state.token}`;
  const resp = await fetch(path, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    let msg = data.detail;
    if (Array.isArray(msg)) msg = msg.map(e => e.msg || JSON.stringify(e)).join(', ');
    throw new Error(msg || `HTTP ${resp.status}`);
  }
  return data;
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

function switchAuthTab(tab) {
  document.getElementById('loginForm').style.display    = tab === 'login'    ? '' : 'none';
  document.getElementById('registerForm').style.display = tab === 'register' ? '' : 'none';
  document.getElementById('tabLogin').classList.toggle('active', tab === 'login');
  document.getElementById('tabRegister').classList.toggle('active', tab === 'register');
}

async function login() {
  const username = document.getElementById('loginUsername').value.trim();
  const password = document.getElementById('loginPassword').value;
  const remember = document.getElementById('rememberMe')?.checked || false;
  const errEl = document.getElementById('loginError');
  errEl.style.display = 'none';
  const btn = document.getElementById('loginBtn');
  btn.disabled = true; btn.innerHTML = '<span class="spinner"></span> Connexion…';

  try {
    const data = await api('POST', '/api/auth/login', { username, password });
    state.token = data.access_token;
    state.username = username;
    sessionStorage.setItem('wf_token', state.token);
    sessionStorage.setItem('wf_user', username);
    if (remember) {
      saveRemembered(username, password);
    } else {
      clearRemembered();
    }
    updateHeaderUI();
    await loadSubscriptionStatus();
    toast(t('welcome') + ', ' + username + ' !', 'success');
    showDash();
  } catch (e) {
    errEl.textContent = e.message;
    errEl.style.display = '';
  } finally {
    btn.disabled = false; btn.innerHTML = 'Continuer →';
  }
}

async function register() {
  const username = document.getElementById('regUsername').value.trim();
  const email    = document.getElementById('regEmail').value.trim();
  const password = document.getElementById('regPassword').value;
  const errEl    = document.getElementById('regError');
  errEl.style.display = 'none';
  const btn = document.getElementById('regBtn');
  btn.disabled = true; btn.innerHTML = '<span class="spinner"></span> Création du compte…';

  try {
    await api('POST', '/api/auth/register', { username, email, password });
    toast('Compte créé ! Connexion en cours…', 'success');
    const data = await api('POST', '/api/auth/login', { username, password });
    state.token = data.access_token;
    state.username = username;
    sessionStorage.setItem('wf_token', state.token);
    sessionStorage.setItem('wf_user', username);
    updateHeaderUI();
    await loadSubscriptionStatus();
    showDash();
  } catch (e) {
    errEl.textContent = e.message;
    errEl.style.display = '';
  } finally {
    btn.disabled = false; btn.innerHTML = 'Créer le compte →';
  }
}

async function logout() {
  try { await api('POST', '/api/auth/logout'); } catch {}
  clearRemembered();
  clearAuth();
  goToStep(1);
  toast(t('logged-out'), 'info');
}

function clearAuth() {
  state.token = null; state.username = null;
  state.subscriptionTier = 'free';
  state.subscriptionFeatures = ['bookmarks', 'history'];
  sessionStorage.removeItem('wf_token');
  sessionStorage.removeItem('wf_user');
  updateHeaderUI();
}

// ---------------------------------------------------------------------------
// Remember me (credentials stored locally for auto-login on app restart)
// ---------------------------------------------------------------------------

function saveRemembered(username, password) {
  localStorage.setItem('wf_remember', btoa(JSON.stringify({ username, password })));
}

function loadRemembered() {
  try {
    const raw = localStorage.getItem('wf_remember');
    if (!raw) return null;
    return JSON.parse(atob(raw));
  } catch { return null; }
}

function clearRemembered() {
  localStorage.removeItem('wf_remember');
}

async function autoLogin(username, password) {
  try {
    const data = await api('POST', '/api/auth/login', { username, password });
    state.token = data.access_token;
    state.username = username;
    sessionStorage.setItem('wf_token', state.token);
    sessionStorage.setItem('wf_user', username);
    updateHeaderUI();
    await loadSubscriptionStatus();
    showDash();
  } catch {
    // Server may have restarted with no session — fall back to login form
    clearRemembered();
    clearAuth();
    // Pre-fill username
    const el = document.getElementById('loginUsername');
    if (el) el.value = username;
  }
}

async function verifyToken() {
  try { await api('GET', '/api/auth/me'); return true; } catch { return false; }
}

function updateHeaderUI() {
  const userEl  = document.getElementById('headerUser');
  const logoutEl = document.getElementById('logoutBtn');
  const tierEl   = document.getElementById('tierBadge');
  const upgradeEl = document.getElementById('upgradeBtn');
  const manageEl  = document.getElementById('manageSubBtn');

  if (state.username) {
    userEl.textContent = '👤 ' + state.username;
    userEl.style.display = '';
    logoutEl.style.display = '';
    tierEl.style.display = '';
    // Upgrade / manage buttons based on tier
    if (state.subscriptionTier === 'beta') {
      // Beta: hide both buttons, everything is unlocked
      upgradeEl.style.display = 'none';
      manageEl.style.display = 'none';
    } else if (state.subscriptionTier === 'free') {
      upgradeEl.style.display = '';
      manageEl.style.display = 'none';
    } else {
      upgradeEl.style.display = 'none';
      manageEl.style.display = '';
    }
  } else {
    userEl.style.display = 'none';
    logoutEl.style.display = 'none';
    tierEl.style.display = 'none';
    upgradeEl.style.display = 'none';
    manageEl.style.display = 'none';
  }
}

// ---------------------------------------------------------------------------
// Subscription
// ---------------------------------------------------------------------------

async function loadSubscriptionStatus() {
  try {
    const data = await api('GET', '/api/billing/status');
    state.subscriptionTier = data.tier || 'free';
    state.subscriptionFeatures = data.features || ['bookmarks', 'history'];
    state.paymentsEnabled = data.payments_enabled || false;
    updateTierBadge(data.tier);
    applyTierToDataTypes(data.tier);
  } catch {
    state.subscriptionTier = 'free';
    state.paymentsEnabled = false;
  }
}

function updateTierBadge(tier) {
  const el = document.getElementById('tierBadge');
  if (!el) return;
  const labels = { free: 'Free', beta: '🧪 Bêta', pro: '⚡ Pro', premium: '👑 Premium' };
  el.textContent = labels[tier] || 'Free';
  el.className = `tier-badge ${tier === 'beta' ? 'pro' : tier}`;
  updateHeaderUI();
}

function applyTierToDataTypes(tier) {
  const proTypes = ['passwords', 'extensions', 'settings'];
  const hasAccess = tier === 'pro' || tier === 'premium' || tier === 'beta';

  proTypes.forEach(type => {
    const card = document.getElementById('dtcard-' + type);
    const lock = document.getElementById('lock-' + type);
    if (!card) return;

    if (hasAccess) {
      card.classList.remove('locked');
      if (lock) lock.style.display = 'none';
      // Auto-select on upgrade
      card.classList.add('selected');
      state.selectedDataTypes.add(type);
    } else {
      card.classList.add('locked');
      card.classList.remove('selected');
      state.selectedDataTypes.delete(type);
      if (lock) lock.style.display = '';
    }
  });
}

// ---------------------------------------------------------------------------
// Step navigation
// ---------------------------------------------------------------------------

function goToStep(n, summary) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.getElementById('page' + n).classList.add('active');
  state.currentStep = n;
  updateProgressBar(n);

  const bar = document.getElementById('progressBar');
  bar.style.display = (n === 1) ? 'none' : 'flex';

  if (n === 2) loadBrowserGrid('source');
  if (n === 4) loadBrowserGrid('dest');
  if (n === 6 && summary) buildSummary(summary);
}

function updateProgressBar(active) {
  for (let i = 1; i <= 6; i++) {
    const dot  = document.getElementById('sdot' + i);
    const line = document.getElementById('sline' + i);
    dot.classList.toggle('active', i === active);
    dot.classList.toggle('done',   i < active);
    if (line) line.classList.toggle('done', i < active);
  }
}

// ---------------------------------------------------------------------------
// Step 2 — Browser detection
// ---------------------------------------------------------------------------

async function loadBrowserGrid(role) {
  if (!state.detectedBrowsers.length) {
    try {
      const data = await api('GET', '/api/browsers/detect');
      state.detectedBrowsers = data.browsers || [];
    } catch (e) {
      toast('Impossible de détecter les navigateurs : ' + e.message, 'error');
      state.detectedBrowsers = [];
    }
  }

  const gridId   = role === 'source' ? 'sourceBrowserGrid' : 'destBrowserGrid';
  const grid     = document.getElementById(gridId);
  grid.innerHTML = '';

  const grouped = {};
  for (const p of state.detectedBrowsers) {
    if (!grouped[p.browser]) grouped[p.browser] = [];
    grouped[p.browser].push(p);
  }

  const allBrowsers = ['chrome', 'firefox', 'opera_gx', 'edge', 'brave'];
  for (const b of allBrowsers) {
    const info     = BROWSER_INFO[b];
    const profiles = grouped[b] || [];
    const avail    = profiles.length > 0;

    const card = document.createElement('div');
    card.className = 'browser-card' + (avail ? '' : ' unavailable');
    card.dataset.browser = b;
    card.innerHTML = `
      <div class="browser-icon" style="background:${info.color}22">${info.emoji}</div>
      <div class="browser-name">${info.label}</div>
      <div class="browser-profiles">${avail ? profiles.length + ' profil(s)' : 'Non détecté'}</div>
    `;
    if (avail) {
      card.onclick = () => selectBrowser(role, b, profiles, card);
    }
    grid.appendChild(card);
  }
}

function selectBrowser(role, browser, profiles, cardEl) {
  const gridId = role === 'source' ? 'sourceBrowserGrid' : 'destBrowserGrid';
  document.querySelectorAll('#' + gridId + ' .browser-card').forEach(c => c.classList.remove('selected'));
  cardEl.classList.add('selected');

  const profileGroupId  = role === 'source' ? 'sourceProfileGroup'  : 'destProfileGroup';
  const profileSelectId = role === 'source' ? 'sourceProfileSelect' : 'destProfileSelect';
  const profileGroup    = document.getElementById(profileGroupId);
  const profileSelect   = document.getElementById(profileSelectId);
  profileSelect.innerHTML = '';
  profiles.forEach(p => {
    const opt = document.createElement('option');
    opt.value = p.path;
    opt.textContent = p.profile + ' — ' + p.path;
    profileSelect.appendChild(opt);
  });
  profileGroup.style.display = '';

  if (role === 'source') {
    state.sourceBrowser = browser;
    state.sourceProfile = profiles[0]?.path;
    profileSelect.onchange = () => { state.sourceProfile = profileSelect.value; };
    document.getElementById('step2Next').disabled = false;
    state.snapshotId = null;
    document.getElementById('step3Next').disabled = true;
    document.getElementById('scanBtn').disabled = false;
    resetCounters();
  } else {
    state.destBrowser = browser;
    state.destProfile = profiles[0]?.path;
    profileSelect.onchange = () => {
      state.destProfile = profileSelect.value;
      checkSameSource();
    };
    checkSameSource();
  }
}

function checkSameSource() {
  const same = state.sourceBrowser === state.destBrowser && state.sourceProfile === state.destProfile;
  document.getElementById('sameSourceWarning').style.display = same ? '' : 'none';
  document.getElementById('step4Next').disabled = !state.destBrowser || same;
}

// ---------------------------------------------------------------------------
// Step 3 — Data type selection & scan
// ---------------------------------------------------------------------------

function toggleDataType(card, type) {
  // Check if locked by subscription tier
  if (!FREE_TYPES.has(type) && state.subscriptionTier === 'free') {
    showPricingModal('pro');
    return;
  }

  card.classList.toggle('selected');
  if (card.classList.contains('selected')) {
    state.selectedDataTypes.add(type);
  } else {
    state.selectedDataTypes.delete(type);
  }
}

function resetCounters() {
  ['bookmarks','history','passwords','extensions','settings'].forEach(t => {
    const el = document.getElementById('count-' + t);
    if (el) el.textContent = 'Non scanné';
  });
}

async function scanBrowser() {
  const btn = document.getElementById('scanBtn');
  const statusEl = document.getElementById('scanStatus');
  const errorEl  = document.getElementById('scanError');
  errorEl.style.display = 'none';
  statusEl.style.display = '';
  btn.disabled = true;

  try {
    const types = Array.from(state.selectedDataTypes);
    const data = await api('POST', '/api/browsers/snapshot', {
      browser: state.sourceBrowser,
      profile: state.sourceProfile,
      data_types: types,
    });

    state.snapshotId = data.id;

    const summary = data.data_summary || {};
    Object.entries(summary).forEach(([type, count]) => {
      const el = document.getElementById('count-' + type);
      if (el) el.textContent = count.toLocaleString() + ' éléments';
    });

    if (data.status === 'error') {
      errorEl.textContent = '⚠️ Scan partiel : ' + (data.error_message || 'Certaines données inaccessibles');
      errorEl.style.display = '';
    }

    document.getElementById('step3Next').disabled = false;
    toast('Navigateur scanné — ' + Object.values(summary).reduce((a,b)=>a+b,0).toLocaleString() + ' éléments trouvés', 'success');
  } catch (e) {
    // If tier-related error, show upgrade modal
    if (e.message && e.message.includes('plan')) {
      showPricingModal('pro');
    } else {
      errorEl.textContent = '❌ ' + e.message;
      errorEl.style.display = '';
      toast('Scan échoué : ' + e.message, 'error');
    }
  } finally {
    statusEl.style.display = 'none';
    btn.disabled = false;
  }
}

// ---------------------------------------------------------------------------
// Step 4 → 5 — Start transfer
// ---------------------------------------------------------------------------

async function startTransfer() {
  goToStep(5);
  const types = Array.from(state.selectedDataTypes);

  const container = document.getElementById('transferProgress');
  container.innerHTML = '';
  types.forEach(type => {
    container.innerHTML += `
      <div class="progress-item" id="prog-${type}">
        <div class="progress-item-header">
          <span>${DATA_TYPE_EMOJI[type] || '📦'} ${type.charAt(0).toUpperCase() + type.slice(1)}</span>
          <span class="status-badge badge-pending" id="badge-${type}">En attente</span>
        </div>
        <div class="progress-bar-track">
          <div class="progress-bar-fill" id="fill-${type}"></div>
        </div>
      </div>`;
  });

  types.forEach(type => {
    setBadge(type, 'running');
    setFill(type, 30);
  });

  try {
    const job = await api('POST', '/api/transfer/start', {
      source_snapshot_id: state.snapshotId,
      target_browser: state.destBrowser,
      target_profile: state.destProfile,
      data_types: types,
    });
    state.jobId = job.id;
    pollJob(types);
  } catch (e) {
    if (e.message && e.message.includes('plan')) {
      goToStep(3);
      showPricingModal('pro');
    } else {
      document.getElementById('transferError').textContent = '❌ ' + e.message;
      document.getElementById('transferError').style.display = '';
      types.forEach(t => { setBadge(t, 'error'); setFill(t, 100, true); });
    }
  }
}

async function pollJob(types) {
  let attempts = 0;
  const maxAttempts = 120;

  const poll = async () => {
    try {
      const job = await api('GET', '/api/transfer/status/' + state.jobId);

      if (job.status === 'running' || job.status === 'pending') {
        types.forEach(t => { setBadge(t, 'running'); setFill(t, 50 + Math.random() * 20); });
        if (attempts++ < maxAttempts) setTimeout(poll, 1000);
        return;
      }

      if (job.status === 'done') {
        const summary = JSON.parse(job.result_summary || '{}');
        types.forEach(t => { setBadge(t, 'done'); setFill(t, 100); });
        state.transferResult = summary;
        setTimeout(() => goToStep(6, summary), 800);
        return;
      }

      if (job.status === 'error') {
        types.forEach(t => { setBadge(t, 'error'); setFill(t, 100, true); });
        document.getElementById('transferError').textContent = '❌ ' + (job.error_message || 'Transfert échoué');
        document.getElementById('transferError').style.display = '';
      }
    } catch (e) {
      if (attempts++ < maxAttempts) setTimeout(poll, 2000);
    }
  };

  poll();
}

function setBadge(type, status) {
  const el = document.getElementById('badge-' + type);
  if (!el) return;
  const labels = { pending: 'En attente', running: 'En cours', done: 'Terminé', error: 'Erreur' };
  el.className = 'status-badge badge-' + status;
  el.textContent = labels[status] || status;
}

function setFill(type, pct, error = false) {
  const el = document.getElementById('fill-' + type);
  if (!el) return;
  el.style.width = pct + '%';
  if (error) el.style.background = 'var(--danger)';
  else if (pct >= 100) el.classList.add('done');
}

// ---------------------------------------------------------------------------
// Step 6 — Summary
// ---------------------------------------------------------------------------

function buildSummary(summary) {
  const grid = document.getElementById('summaryGrid');
  grid.innerHTML = '';
  Object.entries(summary).forEach(([type, count]) => {
    grid.innerHTML += `
      <div class="summary-item">
        <div style="font-size:1.5rem">${DATA_TYPE_EMOJI[type] || '📦'}</div>
        <div class="summary-count">${Number(count).toLocaleString()}</div>
        <div class="summary-label">${type.charAt(0).toUpperCase() + type.slice(1)}</div>
      </div>`;
  });

  if (summary.passwords !== undefined) {
    document.getElementById('passwordNote').style.display = '';
  }
  if (summary.extensions !== undefined) {
    document.getElementById('extensionNote').style.display = '';
  }
}

function downloadReport() {
  const lines = [
    'WebFlow — Rapport de transfert',
    'Date : ' + new Date().toLocaleString(),
    'Source : ' + (BROWSER_INFO[state.sourceBrowser]?.label || state.sourceBrowser) + ' — ' + state.sourceProfile,
    'Destination : ' + (BROWSER_INFO[state.destBrowser]?.label || state.destBrowser) + ' — ' + state.destProfile,
    '',
    'Éléments transférés :',
  ];
  if (state.transferResult) {
    Object.entries(state.transferResult).forEach(([k, v]) => lines.push('  ' + k + ' : ' + v));
  }
  const blob = new Blob([lines.join('\n')], { type: 'text/plain' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'webflow-rapport-' + Date.now() + '.txt';
  a.click();
}

function startOver() {
  state.sourceBrowser = null;
  state.sourceProfile = null;
  state.snapshotId = null;
  state.destBrowser = null;
  state.destProfile = null;
  state.jobId = null;
  state.transferResult = null;
  // Reset selected types to match current tier
  if (state.subscriptionTier === 'free') {
    state.selectedDataTypes = new Set(['bookmarks', 'history']);
  } else {
    state.selectedDataTypes = new Set(['bookmarks', 'history', 'passwords', 'extensions', 'settings']);
  }
  showDash();
}

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------

function showDash() {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.getElementById('pageDash').classList.add('active');
  state.currentStep = 0;
  document.getElementById('progressBar').style.display = 'none';

  const greetEl = document.getElementById('dashGreeting');
  if (greetEl && state.username) {
    greetEl.textContent = 'Bonjour, ' + state.username + ' ! 👋';
  }

  switchDashTab('new');
  updatePlanDetails();
}

function switchDashTab(tab) {
  ['new', 'transfers', 'plan', 'faq'].forEach(t => {
    const btn     = document.getElementById('dtab-' + t);
    const content = document.getElementById('dtab-content-' + t);
    if (btn)     btn.classList.toggle('active', t === tab);
    if (content) content.style.display = (t === tab) ? '' : 'none';
  });
}

function beginTransfer() {
  goToStep(2);
}

function showComingSoonToast() {
  toast(t('coming-soon-toast'), 'info');
}

function updatePlanDetails() {
  const el = document.getElementById('planDetails');
  if (!el) return;
  const tier = state.subscriptionTier;
  const labels = { free: 'Free', beta: '🧪 Bêta', pro: '⚡ Pro', premium: '👑 Premium' };
  const label  = labels[tier] || 'Free';

  let html = `
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px">
      <span class="tier-badge ${tier === 'beta' ? 'pro' : tier}" style="font-size:0.85rem;padding:5px 14px">${label}</span>
      <span style="color:var(--muted);font-size:0.875rem">${t('plan-current-label')}</span>
    </div>
  `;
  if (tier === 'beta') {
    html += `<div class="alert alert-info">${t('plan-msg-beta')}</div>`;
  } else if (tier === 'free') {
    html += `<div class="alert alert-warning">${t('plan-msg-free')}</div>`;
  } else if (tier === 'pro') {
    html += `<div class="alert alert-info">${t('plan-msg-pro')}</div>`;
  } else if (tier === 'premium') {
    html += `<div class="alert alert-info" style="border-color:rgba(255,196,77,0.4);color:#ffc44d">${t('plan-msg-premium')}</div>`;
  }
  el.innerHTML = html;
}

function toggleFaq(el) {
  el.nextElementSibling.classList.toggle('open');
}

// ---------------------------------------------------------------------------
// Pricing modal
// ---------------------------------------------------------------------------

function showPricingModal(suggestedPlan) {
  const modal = document.getElementById('pricingModal');
  modal.style.display = 'flex';

  // Highlight suggested plan card
  if (suggestedPlan) {
    document.querySelectorAll('.pricing-card').forEach(c => c.style.transform = '');
    const target = document.getElementById('pcard-' + suggestedPlan);
    if (target) target.style.transform = 'scale(1.03)';
  }

  // Show current plan badge
  ['free','pro','premium'].forEach(t => {
    const b = document.getElementById('badge-' + t);
    if (b) b.style.display = (t === state.subscriptionTier) ? '' : 'none';
  });

  // Disable checkout buttons for current/lower tiers
  const tier = state.subscriptionTier;
  const btnPro = document.getElementById('btnCheckoutPro');
  const btnPremium = document.getElementById('btnCheckoutPremium');
  if (btnPro)     btnPro.disabled     = (tier === 'pro' || tier === 'premium');
  if (btnPremium) btnPremium.disabled = (tier === 'premium');

  document.getElementById('paymentPendingBox').style.display = 'none';
}

function closePricingModal() {
  document.getElementById('pricingModal').style.display = 'none';
}

async function startCheckout(plan) {
  if (!state.paymentsEnabled) {
    showComingSoonModal();
    return;
  }

  const btn = document.getElementById('btnCheckout' + plan.charAt(0).toUpperCase() + plan.slice(1));
  if (btn) { btn.disabled = true; btn.innerHTML = '<span class="spinner"></span>'; }

  try {
    const data = await api('POST', '/api/billing/checkout/' + plan);
    window.open(data.url, '_blank');
    document.getElementById('paymentPendingBox').style.display = 'flex';
  } catch (e) {
    toast(t('error-prefix') + ' ' + e.message, 'error');
  } finally {
    if (btn) { btn.disabled = false; btn.innerHTML = plan === 'pro' ? t('sub-pro-btn') : t('sub-premium-btn'); }
  }
}

async function refreshSubscription() {
  await loadSubscriptionStatus();
  closePricingModal();
  toast(t('sub-updated') + ' ' + state.subscriptionTier, 'success');
  resetCounters();
}

async function openBillingPortal() {
  if (!state.paymentsEnabled) {
    showComingSoonModal();
    return;
  }
  try {
    const data = await api('POST', '/api/billing/portal');
    window.open(data.url, '_blank');
  } catch (e) {
    toast('Erreur : ' + e.message, 'error');
  }
}

function showComingSoonModal() {
  document.getElementById('comingSoonModal').style.display = 'flex';
}

function closeComingSoonModal() {
  document.getElementById('comingSoonModal').style.display = 'none';
}

// ---------------------------------------------------------------------------
// Toast notifications
// ---------------------------------------------------------------------------

function toast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  const div = document.createElement('div');
  div.className = 'toast ' + type;
  div.textContent = message;
  container.appendChild(div);
  setTimeout(() => div.remove(), 4000);
}
