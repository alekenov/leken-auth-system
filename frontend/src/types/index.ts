// Основные интерфейсы для CRM системы флористов

export interface Client {
  id: number;
  name: string | null;
  phone: string; // +7XXXXXXXXXX
  email: string | null;
  address: string | null;
  client_type: "заказчик" | "получатель" | "оба";
  notes: string | null;
  created_at: string;
}

export interface User {
  id: number;
  username: string;
  email: string;
  city: string | null; // "Алматы" | "Астана"
  position: string | null; // "Менеджер" | "Флорист"
}

export type OrderStatus = "новый" | "в работе" | "готов" | "доставлен";

export interface Order {
  id: number;
  client_id: number;
  recipient_id: number;
  executor_id: number | null;
  status: OrderStatus;
  delivery_date: string; // ISO date
  delivery_address: string;
  total_price: number | null;
  comment: string | null;
  created_at: string; // ISO datetime

  // Связанные данные
  client: Client;
  recipient: Client;
  executor: User | null;
}

export interface OrderListResponse {
  orders: Order[];
  total: number;
  page: number;
  page_size: number;
}

export interface OrderFilters {
  status?: OrderStatus;
  client_phone?: string;
  executor_id?: number;
  date_from?: string;
  date_to?: string;
  min_price?: number;
  max_price?: number;
}

export interface OrderListState {
  orders: Order[];
  loading: boolean;
  error: string | null;
  filters: OrderFilters;
  pagination: {
    page: number;
    page_size: number;
    total: number;
  };
}