# Размещение Halva на Timeweb

Сейчас достаточно локального запуска из README. Для публикации понадобятся домен,
PostgreSQL, SMTP-почта, готовые политика и согласие. Доступ к аккаунту Timeweb и
пароли не нужно передавать в чат: они вводятся в панели или на сервере.

Есть два разных варианта размещения. **App Platform** управляет запуском и HTTPS;
**VPS/VDS** даёт отдельный сервер, который вы обслуживаете. Обычный тариф для
статического/PHP-сайта не следует выбирать, пока не подтверждена возможность
постоянного запуска FastAPI и подключения PostgreSQL.

## App Platform

Для начала ознакомьтесь с официальной
[инструкцией FastAPI](https://timeweb.cloud/docs/apps/deploying-backend-applications/fastapi).
Этот вариант удобен, если не хотите самостоятельно обслуживать Linux.

1. Создайте внешнюю PostgreSQL или используйте существующую доступную серверу базу.
   Не размещайте рабочую SQLite/базу внутри контейнера приложения: новый деплой
   заменяет окружение. Сначала перенесите существующие данные и проверьте резервную копию.
2. Подключите GitHub-репозиторий, выберите проверенную ветку и Python/FastAPI либо
   сборку из нашего Dockerfile. Перед первым рабочим запуском выполните миграции
   `python -m alembic upgrade head` в окружении с параметрами этой базы.
3. Для Python укажите команду установки `pip install -r requirements.txt` и запуск:

   ```bash
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1 --proxy-headers
   ```

   Для Dockerfile порт приложения тоже 8000. `compose.yaml` из репозитория предназначен
   для VPS/локального компьютера: в App Platform запрещены обычные Docker volumes.
4. Перенесите настройки из `.env` в переменные приложения в панели. Установите:
   `APP_ENV=production`, длинный случайный `ADMIN_SECRET_KEY`,
   `ADMIN_SESSION_HTTPS_ONLY=true`, `ALLOWED_HOSTS` со своим доменом, техническим доменом
   и `localhost`. Адреса PostgreSQL/SMTP должны быть доступны из приложения.
5. Укажите только фактические адреса доверенного прокси в `FORWARDED_ALLOW_IPS`.
   Проверьте HTTPS-вход в админку и реальные IP в журнале: эта настройка нужна для
   secure-cookie и ограничителя запросов. Не включайте доверие к заголовкам от любых клиентов.
6. Оставьте один процесс и одну реплику. Настройте SMTP и `EMAIL_WORKER_ENABLED=true`.
   Перезапуск приложения подхватит очередь. Проверка состояния: `/api/health`.
7. Пользователя админки и документы можно создать заранее, запустив команды из README
   с подключением к **этой** внешней базе. Если подключение выполняется с компьютера,
   разрешите его адрес в настройках PostgreSQL только на время обслуживания и используйте
   TLS по инструкции провайдера. Для админки остаётся ключ production-сервера.
8. Откройте технический домен по HTTPS, проверьте сайт, затем подключите свой домен.
   Не включайте автоматическое размещение непроверенных веток.

Подробности: [работа App Platform](https://timeweb.cloud/docs/apps/how-it-works),
[ограничения Docker Compose](https://timeweb.cloud/docs/apps/deploying-with-docker-compose).
Конкретные адреса прокси, реквизиты PostgreSQL, DNS и SMTP определяются выбранной
конфигурацией в панели — их нельзя задать правильно до создания окружения.

## VPS/VDS с Docker

Для этого варианта в репозитории подготовлены `Dockerfile`, `compose.yaml` и Caddy.
Нужны Linux-сервер с Docker Engine/Compose, SSH-доступ и домен. Команды выполняются
на сервере после настройки Docker по официальной документации.

```bash
git clone https://github.com/Kagyasa/Halva-site-fastapi.git
cd Halva-site-fastapi
cp .env.example .env
docker compose build
```

Сначала заполните `.env`. Для production:

```dotenv
APP_ENV=production
ADMIN_SESSION_HTTPS_ONLY=true
ALLOWED_HOSTS=["halva.example.ru","localhost","127.0.0.1"]
PUBLIC_DOMAIN=halva.example.ru
EMAIL_WORKER_ENABLED=true
FORWARDED_ALLOW_IPS=127.0.0.1,172.16.0.0/12
```

`halva.example.ru` здесь пример: замените его своим доменом. Установите настоящие
`DB_PASSWORD`, SMTP-настройки, `ORDERS_EMAIL` и случайный `ADMIN_SECRET_KEY`.
Ключ можно получить на своём компьютере: `python -m app.cli generate-secret`.
`DATABASE_URL` для встроенной базы оставьте незаданным: Compose сам задаёт `DB_HOST=db`.

Домен должен указывать A-записью на IP сервера; если задана AAAA-запись, IPv6 тоже
должен вести на этот сервер. Откройте входящие 80/443 для сайта и SSH для обслуживания.
Порты PostgreSQL и Uvicorn в нашем Compose привязаны к `127.0.0.1`.
Caddy получает и продлевает HTTPS-сертификат для публичного домена автоматически,
если DNS, доступность портов и постоянное хранилище сертификатов настроены правильно.

```bash
docker compose up -d db
docker compose run --rm web python -m alembic upgrade head
docker compose run --rm web python -m app.cli create-admin --username admin --role admin
docker compose --profile https up -d
```

При переносе рабочего сайта сначала восстановите его базу из резервной копии,
затем примените миграцию. Политику и согласие опубликуйте командой из README;
готовые файлы для одноразовой команды можно передать через временное read-only
монтирование либо выполнить команду из локального окружения с защищённым подключением
к серверной базе. До публикации приём заявок закрыт.

Проверьте <https://ваш-домен/admin>, отправку тестовой заявки и статус её письма.
Если очередь остаётся `pending`, проверьте SMTP и логи:

```bash
docker compose logs --tail=100 web
docker compose --profile https logs --tail=100 https
```

У контейнера web непривилегированный пользователь. Прокси должен быть единственным
публичным входом в приложение; не меняйте привязку `127.0.0.1:8000:8000` на `0.0.0.0`.
Если Docker использует другой диапазон адресов, задайте его в `FORWARDED_ALLOW_IPS`.

## Обновления и резервные копии

Перед миграцией сохраните PostgreSQL, например на VPS:

```bash
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > halva-backup.dump
```

Резервная копия содержит персональные данные: храните её с ограниченным доступом
вне репозитория и проверяйте восстановление на отдельной базе. Для App Platform
используйте резервное копирование внешней PostgreSQL.

Обновление VPS после проверки изменений:

```bash
git pull --ff-only
docker compose build
docker compose stop web
docker compose run --rm web python -m alembic upgrade head
docker compose --profile https up -d
```

Фильтр «два месяца» не удаляет заявки. Срок фактического хранения данных необходимо
определить в готовых документах; автоматическое удаление архивов здесь не реализовано.

Официальные источники:

- [Timeweb: FastAPI](https://timeweb.cloud/docs/apps/deploying-backend-applications/fastapi)
- [Timeweb: App Platform и внешние хранилища](https://timeweb.cloud/docs/apps/how-it-works)
- [Timeweb: Docker Compose](https://timeweb.cloud/docs/apps/deploying-with-docker-compose)
- [Caddy: автоматический HTTPS](https://caddyserver.com/docs/automatic-https)
