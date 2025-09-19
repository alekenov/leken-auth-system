import { OrderStatus } from "../types";
import { Badge } from "./ui/badge";

interface OrderStatusBadgeProps {
  status: OrderStatus;
  onChange?: (newStatus: OrderStatus) => void;
  editable?: boolean;
}

const statusConfig = {
  "новый": {
    label: "Новый",
    color: "bg-blue-500 hover:bg-blue-600",
    textColor: "text-white"
  },
  "в работе": {
    label: "В работе", 
    color: "bg-orange-500 hover:bg-orange-600",
    textColor: "text-white"
  },
  "готов": {
    label: "Готов",
    color: "bg-green-500 hover:bg-green-600", 
    textColor: "text-white"
  },
  "доставлен": {
    label: "Доставлен",
    color: "bg-gray-500 hover:bg-gray-600",
    textColor: "text-white"
  }
} as const;

const statusOrder: OrderStatus[] = ["новый", "в работе", "готов", "доставлен"];

export function OrderStatusBadge({ status, onChange, editable = false }: OrderStatusBadgeProps) {
  const config = statusConfig[status];

  const handleClick = () => {
    if (!editable || !onChange) return;
    
    // Переключаем на следующий статус в цикле
    const currentIndex = statusOrder.indexOf(status);
    const nextIndex = (currentIndex + 1) % statusOrder.length;
    onChange(statusOrder[nextIndex]);
  };

  return (
    <Badge
      className={`${config.color} ${config.textColor} ${editable ? 'cursor-pointer' : ''}`}
      onClick={handleClick}
      title={editable ? "Нажмите для изменения статуса" : undefined}
    >
      {config.label}
    </Badge>
  );
}