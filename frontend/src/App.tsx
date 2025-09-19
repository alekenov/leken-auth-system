import { OrdersList } from "./components/OrdersList";
import { Toaster } from "./components/ui/sonner";

export default function App() {
  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-8">
        <OrdersList />
      </div>
      <Toaster />
    </div>
  );
}