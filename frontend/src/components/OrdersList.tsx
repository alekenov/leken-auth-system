import { useState, useEffect } from "react";
import { Order, OrderFilters, OrderStatus, OrderListState, User } from "../types";
import { apiService } from "../lib/apiService";
import { OrderFilters as OrderFiltersComponent } from "./OrderFilters";
import { OrderTable } from "./OrderTable";
import { OrderPagination } from "./OrderPagination";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Badge } from "./ui/badge";
import { toast } from "sonner@2.0.3";
import { Loader2, Package, RefreshCw } from "lucide-react";
import { Button } from "./ui/button";

export function OrdersList() {
  const [state, setState] = useState<OrderListState>({
    orders: [],
    loading: true,
    error: null,
    filters: {},
    pagination: {
      page: 1,
      page_size: 20,
      total: 0
    }
  });

  const [users, setUsers] = useState<User[]>([]);
  const [usersLoading, setUsersLoading] = useState(true);

  // Загрузка пользователей
  const loadUsers = async () => {
    try {
      setUsersLoading(true);
      const usersList = await apiService.getUsers();
      setUsers(usersList);
    } catch (error) {
      console.error('Failed to load users:', error);
      toast.error("Не удалось загрузить список пользователей");
    } finally {
      setUsersLoading(false);
    }
  };

  // Загрузка данных
  const loadOrders = async (
    filters: OrderFilters = state.filters,
    page: number = state.pagination.page,
    pageSize: number = state.pagination.page_size
  ) => {
    setState(prev => ({ ...prev, loading: true, error: null }));

    try {
      const response = await apiService.getOrders(filters, page, pageSize);

      setState(prev => ({
        ...prev,
        orders: response.orders,
        pagination: {
          page: response.page,
          page_size: response.page_size,
          total: response.total
        },
        loading: false
      }));
    } catch (error) {
      setState(prev => ({
        ...prev,
        loading: false,
        error: "Ошибка загрузки заказов"
      }));
      toast.error("Не удалось загрузить заказы");
    }
  };

  // Первоначальная загрузка
  useEffect(() => {
    loadUsers();
    loadOrders();
  }, []);

  // Обработчики фильтров
  const handleFiltersChange = (newFilters: OrderFilters) => {
    setState(prev => ({
      ...prev,
      filters: newFilters,
      pagination: { ...prev.pagination, page: 1 }
    }));
    loadOrders(newFilters, 1, state.pagination.page_size);
  };

  // Обработчики пагинации
  const handlePageChange = (page: number) => {
    loadOrders(state.filters, page, state.pagination.page_size);
  };

  const handlePageSizeChange = (pageSize: number) => {
    loadOrders(state.filters, 1, pageSize);
  };

  // Изменение статуса заказа
  const handleStatusChange = async (orderId: number, newStatus: OrderStatus) => {
    try {
      await apiService.updateOrderStatus(orderId, newStatus);

      // Обновляем локальное состояние
      setState(prev => ({
        ...prev,
        orders: prev.orders.map(order =>
          order.id === orderId ? { ...order, status: newStatus } : order
        )
      }));

      toast.success(`Статус заказа #${orderId} изменен на "${newStatus}"`);
    } catch (error) {
      toast.error("Не удалось изменить статус заказа");
    }
  };

  // Назначение исполнителя
  const handleExecutorChange = async (orderId: number, executorId: number | null) => {
    try {
      await apiService.updateOrderExecutor(orderId, executorId);

      const executor = executorId ? users.find(u => u.id === executorId) || null : null;

      // Обновляем локальное состояние
      setState(prev => ({
        ...prev,
        orders: prev.orders.map(order =>
          order.id === orderId
            ? { ...order, executor_id: executorId, executor }
            : order
        )
      }));

      const message = executorId
        ? `Исполнитель назначен для заказа #${orderId}`
        : `Исполнитель убран с заказа #${orderId}`;
      toast.success(message);
    } catch (error) {
      toast.error("Не удалось изменить исполнителя");
    }
  };

  // Просмотр заказа
  const handleViewOrder = (orderId: number) => {
    toast.info(`Просмотр заказа #${orderId} (функция в разработке)`);
  };

  // Редактирование заказа
  const handleEditOrder = (orderId: number) => {
    toast.info(`Редактирование заказа #${orderId} (функция в разработке)`);
  };

  // Обновление данных
  const handleRefresh = () => {
    loadOrders();
    toast.success("Данные обновлены");
  };

  const totalPages = Math.ceil(state.pagination.total / state.pagination.page_size);

  // Статистика по статусам
  const getStatusStats = () => {
    const stats = state.orders.reduce((acc, order) => {
      acc[order.status] = (acc[order.status] || 0) + 1;
      return acc;
    }, {} as Record<OrderStatus, number>);

    return [
      { status: "новый" as OrderStatus, count: stats["новый"] || 0, color: "bg-blue-500" },
      { status: "в работе" as OrderStatus, count: stats["в работе"] || 0, color: "bg-orange-500" },
      { status: "готов" as OrderStatus, count: stats["готов"] || 0, color: "bg-green-500" },
      { status: "доставлен" as OrderStatus, count: stats["доставлен"] || 0, color: "bg-gray-500" }
    ];
  };

  return (
    <div className="space-y-6">
      {/* Заголовок и статистика */}
      <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold">Управление заказами</h1>
          <p className="text-muted-foreground mt-1">
            CRM система для флористов
          </p>
        </div>
        
        <div className="flex flex-wrap gap-2">
          {getStatusStats().map(({ status, count, color }) => (
            <Badge key={status} variant="outline" className="gap-2">
              <div className={`w-2 h-2 rounded-full ${color}`} />
              {status}: {count}
            </Badge>
          ))}
        </div>
      </div>

      {/* Фильтры */}
      <OrderFiltersComponent
        filters={state.filters}
        onFiltersChange={handleFiltersChange}
        executors={users}
        loading={state.loading || usersLoading}
      />

      {/* Главная таблица */}
      <Card>
        <CardHeader>
          <div className="flex justify-between items-center">
            <CardTitle className="flex items-center gap-2">
              <Package className="h-5 w-5" />
              Список заказов
            </CardTitle>
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefresh}
              disabled={state.loading}
            >
              {state.loading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4" />
              )}
              Обновить
            </Button>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <OrderTable
            orders={state.orders}
            executors={users}
            loading={state.loading || usersLoading}
            onStatusChange={handleStatusChange}
            onExecutorChange={handleExecutorChange}
            onViewOrder={handleViewOrder}
            onEditOrder={handleEditOrder}
          />
        </CardContent>
      </Card>

      {/* Пагинация */}
      {totalPages > 0 && (
        <OrderPagination
          currentPage={state.pagination.page}
          totalPages={totalPages}
          pageSize={state.pagination.page_size}
          totalItems={state.pagination.total}
          onPageChange={handlePageChange}
          onPageSizeChange={handlePageSizeChange}
          loading={state.loading}
        />
      )}

      {/* Ошибка */}
      {state.error && (
        <Card className="border-destructive">
          <CardContent className="pt-6">
            <p className="text-destructive">{state.error}</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}