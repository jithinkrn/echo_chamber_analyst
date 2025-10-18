#!/bin/sh
set -e

cd /app
echo "→ Entrypoint starting"

# Optional: wait for DB to be reachable
if [ "${WAIT_FOR_DB:-1}" = "1" ]; then
  echo "→ Waiting for database…"
  python - <<'PY'
import os, time, sys
os.environ.setdefault("DJANGO_SETTINGS_MODULE", os.getenv("DJANGO_SETTINGS_MODULE","config.settings"))
from django.core.wsgi import get_wsgi_application
get_wsgi_application()
from django.db import connections
for i in range(45):
    try:
        connections['default'].cursor()
        print("DB up")
        break
    except Exception as e:
        print("DB not ready yet:", e)
        time.sleep(2)
else:
    sys.exit("Timed out waiting for DB")
PY
fi

# 1) Migrations (idempotent)
if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
  echo "→ Running migrations…"
  python manage.py migrate --noinput
fi

# 2) Your admin + base test data (idempotent within command)
#    /backend/common/management/commands/create_test_data.py
if [ "${CREATE_TEST_DATA:-1}" = "1" ]; then
  echo "→ Ensuring admin & test data…"
  python manage.py create_test_data ${TESTDATA_ARGS:-} || echo "create_test_data returned non-zero; continuing"
fi

# 3) Optional: detailed analytics seed
#    /backend/common/management/commands/create_detailed_analytics_data.py
if [ "${CREATE_DETAILED_ANALYTICS:-0}" = "1" ]; then
  echo "→ Ensuring detailed analytics data…"
  python manage.py create_detailed_analytics_data ${ANALYTICS_ARGS:-} || echo "create_detailed_analytics_data returned non-zero; continuing"
fi

# 4) Collect static (runtime, optional)
if [ "${COLLECTSTATIC:-1}" = "1" ]; then
  echo "→ Collecting static…"
  python manage.py collectstatic --noinput || true
fi

echo "→ Starting app: $*"
exec "$@"
