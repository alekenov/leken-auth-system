import { Button } from "./ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";
import { ChevronLeft, ChevronRight } from "lucide-react";

interface OrderPaginationProps {
  currentPage: number;
  totalPages: number;
  pageSize: number;
  totalItems: number;
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: number) => void;
  loading?: boolean;
}

export function OrderPagination({
  currentPage,
  totalPages,
  pageSize,
  totalItems,
  onPageChange,
  onPageSizeChange,
  loading
}: OrderPaginationProps) {
  const startItem = Math.min((currentPage - 1) * pageSize + 1, totalItems);
  const endItem = Math.min(currentPage * pageSize, totalItems);

  // Генерируем номера страниц для отображения
  const getPageNumbers = () => {
    const pages: (number | string)[] = [];
    const maxVisible = 5; // Максимум видимых номеров страниц
    
    if (totalPages <= maxVisible) {
      // Показываем все страницы если их мало
      for (let i = 1; i <= totalPages; i++) {
        pages.push(i);
      }
    } else {
      // Логика для большого количества страниц
      if (currentPage <= 3) {
        // Начало списка
        for (let i = 1; i <= 4; i++) {
          pages.push(i);
        }
        pages.push('...');
        pages.push(totalPages);
      } else if (currentPage >= totalPages - 2) {
        // Конец списка
        pages.push(1);
        pages.push('...');
        for (let i = totalPages - 3; i <= totalPages; i++) {
          pages.push(i);
        }
      } else {
        // Середина списка
        pages.push(1);
        pages.push('...');
        for (let i = currentPage - 1; i <= currentPage + 1; i++) {
          pages.push(i);
        }
        pages.push('...');
        pages.push(totalPages);
      }
    }
    
    return pages;
  };

  const pageSizes = [10, 20, 50, 100];

  return (
    <div className="flex flex-col sm:flex-row items-center justify-between gap-4 mt-6">
      {/* Информация о количестве */}
      <div className="text-sm text-muted-foreground">
        Показано {startItem}-{endItem} из {totalItems} заказов
      </div>

      <div className="flex flex-col sm:flex-row items-center gap-4">
        {/* Выбор размера страницы */}
        <div className="flex items-center gap-2">
          <span className="text-sm">Показывать по:</span>
          <Select
            value={pageSize.toString()}
            onValueChange={(value) => onPageSizeChange(parseInt(value))}
            disabled={loading}
          >
            <SelectTrigger className="w-20">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {pageSizes.map((size) => (
                <SelectItem key={size} value={size.toString()}>
                  {size}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Навигация по страницам */}
        {totalPages > 1 && (
          <div className="flex items-center gap-2">
            {/* Предыдущая страница */}
            <Button
              variant="outline"
              size="sm"
              onClick={() => onPageChange(currentPage - 1)}
              disabled={currentPage === 1 || loading}
            >
              <ChevronLeft className="h-4 w-4" />
              Предыдущая
            </Button>

            {/* Номера страниц */}
            <div className="flex gap-1">
              {getPageNumbers().map((page, index) => (
                <Button
                  key={index}
                  variant={page === currentPage ? "default" : "outline"}
                  size="sm"
                  className="w-10"
                  onClick={() => typeof page === 'number' ? onPageChange(page) : undefined}
                  disabled={typeof page !== 'number' || loading}
                >
                  {page}
                </Button>
              ))}
            </div>

            {/* Следующая страница */}
            <Button
              variant="outline"
              size="sm"
              onClick={() => onPageChange(currentPage + 1)}
              disabled={currentPage === totalPages || loading}
            >
              Следующая
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}