import { Order, User, OrderStatus } from "../types";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "./ui/table";
import { Button } from "./ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";
import { OrderStatusBadge } from "./OrderStatusBadge";
import { Skeleton } from "./ui/skeleton";
import { Eye, Edit } from "lucide-react";

interface OrderTableProps {
  orders: Order[];
  executors: User[];
  loading?: boolean;
  onStatusChange: (orderId: number, newStatus: OrderStatus) => void;
  onExecutorChange: (orderId: number, executorId: number | null) => void;
  onViewOrder: (orderId: number) => void;
  onEditOrder: (orderId: number) => void;
}

export function OrderTable({
  orders,
  executors,
  loading,
  onStatusChange,
  onExecutorChange,
  onViewOrder,
  onEditOrder
}: OrderTableProps) {
  const formatPrice = (price: number | null) => {
    if (!price) return "—";
    return new Intl.NumberFormat('ru-RU').format(price) + " ₸";
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric'
    });
  };

  const formatClientInfo = (client: Order['client']) => (
    <div className="space-y-1">
      <div className="font-medium">{client.name || "Без имени"}</div>
      <div className="text-sm text-muted-foreground">{client.phone}</div>
    </div>
  );

  if (loading) {
    return (
      <div className="space-y-3">
        {[...Array(5)].map((_, i) => (
          <Skeleton key={i} className="h-20 w-full" />
        ))}
      </div>
    );
  }

  return (
    <div className="border rounded-lg overflow-hidden">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-16">ID</TableHead>
            <TableHead className="min-w-40">Клиент</TableHead>
            <TableHead className="min-w-40">Получатель</TableHead>
            <TableHead className="w-32">Статус</TableHead>
            <TableHead className="w-32">Дата доставки</TableHead>
            <TableHead className="w-28">Сумма</TableHead>
            <TableHead className="min-w-40">Исполнитель</TableHead>
            <TableHead className="w-32">Действия</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {orders.length === 0 ? (
            <TableRow>
              <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">
                Заказы не найдены
              </TableCell>
            </TableRow>
          ) : (
            orders.map((order) => (
              <TableRow key={order.id} className="hover:bg-muted/50">
                <TableCell>
                  <Button 
                    variant="link" 
                    className="p-0 h-auto font-mono"
                    onClick={() => onViewOrder(order.id)}
                  >
                    #{order.id}
                  </Button>
                </TableCell>
                
                <TableCell>
                  {formatClientInfo(order.client)}
                </TableCell>
                
                <TableCell>
                  {order.client_id === order.recipient_id ? (
                    <span className="text-muted-foreground text-sm">тот же</span>
                  ) : (
                    formatClientInfo(order.recipient)
                  )}
                </TableCell>
                
                <TableCell>
                  <OrderStatusBadge
                    status={order.status}
                    editable
                    onChange={(newStatus) => onStatusChange(order.id, newStatus)}
                  />
                </TableCell>
                
                <TableCell className="text-sm">
                  {formatDate(order.delivery_date)}
                </TableCell>
                
                <TableCell className="text-sm">
                  {formatPrice(order.total_price)}
                </TableCell>
                
                <TableCell>
                  <Select
                    value={order.executor_id?.toString() || "none"}
                    onValueChange={(value) => 
                      onExecutorChange(order.id, value === 'none' ? null : parseInt(value))
                    }
                  >
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="Не назначен" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">Не назначен</SelectItem>
                      {executors.map((executor) => (
                        <SelectItem key={executor.id} value={executor.id.toString()}>
                          <div className="flex flex-col text-left">
                            <span>{executor.username}</span>
                            <span className="text-xs text-muted-foreground">
                              {executor.position} • {executor.city}
                            </span>
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </TableCell>
                
                <TableCell>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => onViewOrder(order.id)}
                      title="Просмотр"
                    >
                      <Eye className="h-4 w-4" />
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => onEditOrder(order.id)}
                      title="Редактировать"
                    >
                      <Edit className="h-4 w-4" />
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </div>
  );
}