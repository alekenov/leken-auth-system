#!/bin/bash

# Цвета для вывода
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo "=== Тестирование API ==="

# 1. Регистрация пользователя
echo -e "\n1. Регистрация пользователя test_orders..."
REGISTER=$(curl -s -X POST http://localhost:8011/register \
  -H "Content-Type: application/json" \
  -d '{"username":"test_orders","password":"test123","email":"orders@test.com"}' 2>/dev/null)

if [ $? -eq 0 ]; then
  echo -e "${GREEN}✓ Регистрация успешна или пользователь уже существует${NC}"
else
  echo -e "${RED}✗ Ошибка регистрации${NC}"
fi

# 2. Логин
echo -e "\n2. Логин..."
TOKEN=$(curl -s -X POST http://localhost:8011/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test_orders","password":"test123"}' | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)

if [ -n "$TOKEN" ]; then
  echo -e "${GREEN}✓ Токен получен${NC}"
else
  echo -e "${RED}✗ Не удалось получить токен${NC}"
  exit 1
fi

# 3. Получение заказов
echo -e "\n3. Получение списка заказов..."
ORDERS=$(curl -s -H "Authorization: Bearer $TOKEN" \
  -H "Origin: http://localhost:8888" \
  http://localhost:8011/api/orders)

if echo "$ORDERS" | python3 -m json.tool > /dev/null 2>&1; then
  echo -e "${GREEN}✓ Заказы получены успешно${NC}"
  echo "$ORDERS" | python3 -m json.tool | head -20
else
  echo -e "${RED}✗ Ошибка получения заказов${NC}"
  echo "$ORDERS"
fi

# 4. Проверка CORS заголовков
echo -e "\n4. Проверка CORS заголовков..."
CORS=$(curl -s -I -H "Origin: http://localhost:8888" \
  -H "Authorization: Bearer $TOKEN" \
  http://localhost:8011/api/orders 2>&1 | grep -i "access-control")

if [ -n "$CORS" ]; then
  echo -e "${GREEN}✓ CORS заголовки присутствуют:${NC}"
  echo "$CORS"
else
  echo -e "${RED}✗ CORS заголовки отсутствуют${NC}"
fi

echo -e "\n=== Тестирование завершено ==="
