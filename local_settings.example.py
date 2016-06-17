DEBUG = True
ALLOWED_HOSTS = ["locahost:8000"]

ACCOUNT_DEFAULT_HTTP_PROTOCOL = "http"

DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"
MEDIA_URL = "/media/"
STATIC_URL = "/static/"
JOUST_STATIC_URL = "//static.hsreplay.net/static/joust/"
# JOUST_RAVEN_DSN_PUBLIC = "https://hash@app.getsentry.com/12345"

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

INTERNAL_IPS = (
	"0.0.0.0",
	"127.0.0.1",
)

RAVEN_CONFIG = {
	"dsn": "https://******@app.getsentry.com/80388",
	# If you are using git, you can also automatically configure the
	# release based on the git info.
	# "release": raven.fetch_git_sha(os.path.join(os.path.dirname(__file__), "..")),
}
