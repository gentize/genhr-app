from employee_portal import create_app
from werkzeug.middleware.proxy_fix import ProxyFix
import os

app = create_app()

# Handle reverse proxy headers (Nginx)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_host=1, x_proto=1, x_prefix=1)

if __name__ == '__main__':
    app.run(debug=True)
