# Primix v1.0

Монолитный асинхронный бэкенд-рантайм. Ноль зависимостей. Чистый Python 3.8+.

## Структура
- `primix.py` — ядро интерпретатора и сервера.
- `server.pmx` — логика сервера (маршруты, переменные, безопасность).

## Запуск
```bash
python primix.py server.pmx
```

Синтаксис .pmx
 Маршруты
```pmx
go request /path then
    respond "GET response"

go fields /path then
    respond "POST response"
```

Переменные и хранение
pmx
counter = 0
counter = counter + 1
store on/ my_key
data = get to/ my_key


### Управление и безопасность
pmx
log on / off
cache on / clear cache
queue on
/add t8t mixed      # Режимы: mixed, jp, en, rnd
whitelist key_name
block key enemy_key
lock down           # Включает physical only, ghost, blackhole
burn server         # Аварийная остановка


 Периодические задачи
pmx
every 5 min do
    print "Alive"


База данных и файлы
pmx
db query "SELECT * FROM users"
file read "config.txt"
file write "log.txt" "content"


Архитектура
- Asyncio неблокирующий ввод-вывод, keep-alive соединения.
- **Кэш**: LRU-подобная очистка при превышении 10 000 записей.
- **T8T**: встроенное обфусцированное шифрование ответов (mixed/jp/en/rnd).
- **Безопасность**: ротация ключей, whitelist/blacklist, режимы blackhole и lock down.
