import { useState } from "react";
import { OrderFilters as OrderFiltersType, OrderStatus, User } from "../types";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Label } from "./ui/label";
import { Search, X } from "lucide-react";

interface OrderFiltersProps {
  filters: OrderFiltersType;
  onFiltersChange: (filters: OrderFiltersType) => void;
  executors: User[];
  loading?: boolean;
}

export function OrderFilters({ filters, onFiltersChange, executors, loading }: OrderFiltersProps) {
  const [localFilters, setLocalFilters] = useState<OrderFiltersType>(filters);

  const handleFilterChange = (key: keyof OrderFiltersType, value: any) => {
    setLocalFilters(prev => ({
      ...prev,
      [key]: value || undefined
    }));
  };

  const handleSearch = () => {
    onFiltersChange(localFilters);
  };

  const handleReset = () => {
    const emptyFilters: OrderFiltersType = {};
    setLocalFilters(emptyFilters);
    onFiltersChange(emptyFilters);
  };

  const statuses: { value: OrderStatus; label: string }[] = [
    { value: "новый", label: "Новый" },
    { value: "в работе", label: "В работе" },
    { value: "готов", label: "Готов" },
    { value: "доставлен", label: "Доставлен" }
  ];

  return (
    <Card className="mb-6">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Search className="h-5 w-5" />
          Фильтры поиска
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 mb-4">
          {/* Поиск по телефону */}
          <div className="space-y-2">
            <Label htmlFor="phone">Поиск по телефону</Label>
            <Input
              id="phone"
              placeholder="+7XXXXXXXXXX"
              value={localFilters.client_phone || ''}
              onChange={(e) => handleFilterChange('client_phone', e.target.value)}
            />
          </div>

          {/* Статус */}
          <div className="space-y-2">
            <Label>Статус</Label>
            <Select 
              value={localFilters.status || "all"} 
              onValueChange={(value) => handleFilterChange('status', value === 'all' ? null : value)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Все статусы" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Все статусы</SelectItem>
                {statuses.map(status => (
                  <SelectItem key={status.value} value={status.value}>
                    {status.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Исполнитель */}
          <div className="space-y-2">
            <Label>Исполнитель</Label>
            <Select 
              value={localFilters.executor_id?.toString() || "all"} 
              onValueChange={(value) => handleFilterChange('executor_id', value === 'all' ? null : parseInt(value))}
            >
              <SelectTrigger>
                <SelectValue placeholder="Все исполнители" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Все исполнители</SelectItem>
                {executors.map(executor => (
                  <SelectItem key={executor.id} value={executor.id.toString()}>
                    {executor.username} ({executor.position})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Дата доставки от */}
          <div className="space-y-2">
            <Label htmlFor="date_from">Дата доставки от</Label>
            <Input
              id="date_from"
              type="date"
              value={localFilters.date_from || ''}
              onChange={(e) => handleFilterChange('date_from', e.target.value)}
            />
          </div>

          {/* Дата доставки до */}
          <div className="space-y-2">
            <Label htmlFor="date_to">Дата доставки до</Label>
            <Input
              id="date_to"
              type="date"
              value={localFilters.date_to || ''}
              onChange={(e) => handleFilterChange('date_to', e.target.value)}
            />
          </div>

          {/* Минимальная сумма */}
          <div className="space-y-2">
            <Label htmlFor="min_price">Мин. сумма (₸)</Label>
            <Input
              id="min_price"
              type="number"
              placeholder="0"
              value={localFilters.min_price || ''}
              onChange={(e) => handleFilterChange('min_price', e.target.value ? parseInt(e.target.value) : null)}
            />
          </div>

          {/* Максимальная сумма */}
          <div className="space-y-2">
            <Label htmlFor="max_price">Макс. сумма (₸)</Label>
            <Input
              id="max_price"
              type="number"
              placeholder="∞"
              value={localFilters.max_price || ''}
              onChange={(e) => handleFilterChange('max_price', e.target.value ? parseInt(e.target.value) : null)}
            />
          </div>
        </div>

        {/* Кнопки действий */}
        <div className="flex gap-3">
          <Button onClick={handleSearch} disabled={loading}>
            <Search className="h-4 w-4 mr-2" />
            Найти
          </Button>
          <Button variant="outline" onClick={handleReset} disabled={loading}>
            <X className="h-4 w-4 mr-2" />
            Сбросить фильтры
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}