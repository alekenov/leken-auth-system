import { Order, OrderFilters, OrderListResponse, OrderStatus, User } from "../types";

const API_BASE_URL = 'http://localhost:8011/api';

class ApiService {
  private async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        headers: {
          'Content-Type': 'application/json',
          ...options?.headers,
        },
        ...options,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error(`API request failed for ${endpoint}:`, error);
      throw error;
    }
  }

  // Получить список заказов с фильтрацией и пагинацией
  async getOrders(
    filters: OrderFilters = {},
    page: number = 1,
    pageSize: number = 20
  ): Promise<OrderListResponse> {
    const params = new URLSearchParams();

    // Добавляем пагинацию
    params.append('page', page.toString());
    params.append('page_size', pageSize.toString());

    // Добавляем фильтры если они есть
    if (filters.status) {
      params.append('status', filters.status);
    }
    if (filters.client_phone) {
      params.append('client_phone', filters.client_phone);
    }
    if (filters.executor_id) {
      params.append('executor_id', filters.executor_id.toString());
    }
    if (filters.date_from) {
      params.append('date_from', filters.date_from);
    }
    if (filters.date_to) {
      params.append('date_to', filters.date_to);
    }
    if (filters.min_price) {
      params.append('min_price', filters.min_price.toString());
    }
    if (filters.max_price) {
      params.append('max_price', filters.max_price.toString());
    }

    const response = await this.request<OrderListResponse>(`/orders/search?${params.toString()}`);

    // Возвращаем ответ от API напрямую, так как он уже в правильном формате
    return response;
  }

  // Получить один заказ по ID
  async getOrder(id: number): Promise<Order> {
    return this.request<Order>(`/orders/${id}`);
  }

  // Обновить статус заказа
  async updateOrderStatus(orderId: number, status: OrderStatus): Promise<Order> {
    return this.request<Order>(`/orders/${orderId}`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    });
  }

  // Назначить исполнителя заказу
  async updateOrderExecutor(orderId: number, executorId: number | null): Promise<Order> {
    return this.request<Order>(`/orders/${orderId}`, {
      method: 'PATCH',
      body: JSON.stringify({ executor_id: executorId }),
    });
  }

  // Получить список пользователей (флористов)
  async getUsers(): Promise<User[]> {
    return this.request<User[]>('/users');
  }

  // Создать новый заказ
  async createOrder(orderData: Partial<Order>): Promise<Order> {
    return this.request<Order>('/orders', {
      method: 'POST',
      body: JSON.stringify(orderData),
    });
  }

  // Обновить заказ
  async updateOrder(orderId: number, orderData: Partial<Order>): Promise<Order> {
    return this.request<Order>(`/orders/${orderId}`, {
      method: 'PUT',
      body: JSON.stringify(orderData),
    });
  }

  // Удалить заказ
  async deleteOrder(orderId: number): Promise<void> {
    return this.request<void>(`/orders/${orderId}`, {
      method: 'DELETE',
    });
  }
}

// Экспортируем единый экземпляр сервиса
export const apiService = new ApiService();

// Функция-обертка для совместимости с существующим кодом
export const realApiCall = async (
  filters: OrderFilters = {},
  page: number = 1,
  pageSize: number = 20
): Promise<OrderListResponse> => {
  return apiService.getOrders(filters, page, pageSize);
};