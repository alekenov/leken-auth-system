import { Order, Client, User, OrderListResponse } from "../types";

// Моковые данные для разработки
export const mockClients: Client[] = [
  {
    id: 1,
    name: "Анна Петрова",
    phone: "+77012345678",
    email: "anna@example.com",
    address: "ул. Абая 150, кв. 25",
    client_type: "заказчик",
    notes: null,
    created_at: "2024-01-15T10:30:00Z"
  },
  {
    id: 2,
    name: "Мария Иванова",
    phone: "+77087654321",
    email: "maria@example.com",
    address: "пр. Достык 240, офис 15",
    client_type: "получатель",
    notes: null,
    created_at: "2024-01-20T14:15:00Z"
  },
  {
    id: 3,
    name: "Елена Смирнова",
    phone: "+77051234567",
    email: null,
    address: "ул. Назарбаева 75",
    client_type: "оба",
    notes: "Постоянный клиент",
    created_at: "2024-02-01T09:00:00Z"
  }
];

export const mockUsers: User[] = [
  {
    id: 1,
    username: "aidana_flores",
    email: "aidana@flores.kz",
    city: "Алматы",
    position: "Флорист"
  },
  {
    id: 2,
    username: "dmitry_manager",
    email: "dmitry@flores.kz", 
    city: "Алматы",
    position: "Менеджер"
  },
  {
    id: 3,
    username: "sara_astana",
    email: "sara@flores.kz",
    city: "Астана", 
    position: "Флорист"
  }
];

export const mockOrders: Order[] = [
  {
    id: 1,
    client_id: 1,
    recipient_id: 2,
    executor_id: 1,
    status: "новый",
    delivery_date: "2024-12-25T00:00:00Z",
    delivery_address: "пр. Достык 240, офис 15",
    total_price: 15000,
    comment: "Букет из роз и лилий",
    created_at: "2024-12-20T10:30:00Z",
    client: mockClients[0],
    recipient: mockClients[1],
    executor: mockUsers[0]
  },
  {
    id: 2,
    client_id: 2,
    recipient_id: 3,
    executor_id: null,
    status: "в работе",
    delivery_date: "2024-12-26T00:00:00Z", 
    delivery_address: "ул. Назарбаева 75",
    total_price: 25000,
    comment: null,
    created_at: "2024-12-19T15:45:00Z",
    client: mockClients[1],
    recipient: mockClients[2],
    executor: null
  },
  {
    id: 3,
    client_id: 3,
    recipient_id: 3,
    executor_id: 2,
    status: "готов",
    delivery_date: "2024-12-24T00:00:00Z",
    delivery_address: "ул. Назарбаева 75",
    total_price: 8000,
    comment: "Небольшая композиция",
    created_at: "2024-12-18T12:00:00Z",
    client: mockClients[2],
    recipient: mockClients[2],
    executor: mockUsers[1]
  },
  {
    id: 4,
    client_id: 1,
    recipient_id: 1,
    executor_id: 3,
    status: "доставлен",
    delivery_date: "2024-12-23T00:00:00Z",
    delivery_address: "ул. Абая 150, кв. 25",
    total_price: 12000,
    comment: "Букет на день рождения",
    created_at: "2024-12-17T09:15:00Z",
    client: mockClients[0],
    recipient: mockClients[0],
    executor: mockUsers[2]
  }
];

// Имитация API
export const mockApiCall = async (
  filters: any = {},
  page: number = 1,
  pageSize: number = 20
): Promise<OrderListResponse> => {
  await new Promise(resolve => setTimeout(resolve, 500)); // Имитация задержки сети
  
  let filteredOrders = [...mockOrders];

  // Применяем фильтры
  if (filters.status) {
    filteredOrders = filteredOrders.filter(order => order.status === filters.status);
  }

  if (filters.client_phone) {
    filteredOrders = filteredOrders.filter(order => 
      order.client.phone.includes(filters.client_phone) ||
      order.recipient.phone.includes(filters.client_phone)
    );
  }

  if (filters.executor_id) {
    filteredOrders = filteredOrders.filter(order => order.executor_id === filters.executor_id);
  }

  if (filters.date_from) {
    filteredOrders = filteredOrders.filter(order => 
      new Date(order.delivery_date) >= new Date(filters.date_from)
    );
  }

  if (filters.date_to) {
    filteredOrders = filteredOrders.filter(order => 
      new Date(order.delivery_date) <= new Date(filters.date_to)
    );
  }

  if (filters.min_price) {
    filteredOrders = filteredOrders.filter(order => 
      order.total_price && order.total_price >= filters.min_price
    );
  }

  if (filters.max_price) {
    filteredOrders = filteredOrders.filter(order => 
      order.total_price && order.total_price <= filters.max_price
    );
  }

  // Сортировка по дате создания (новые сверху)
  filteredOrders.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

  // Пагинация
  const startIndex = (page - 1) * pageSize;
  const endIndex = startIndex + pageSize;
  const paginatedOrders = filteredOrders.slice(startIndex, endIndex);

  return {
    orders: paginatedOrders,
    total: filteredOrders.length,
    page,
    page_size: pageSize
  };
};