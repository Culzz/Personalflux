import { Link } from "react-router-dom";
import { EmptyState } from "../components/States";

export default function NotFoundPage() {
  return (
    <EmptyState title="Page not found">
      <Link to="/" className="text-violet-300 underline">Go to the home page</Link>
    </EmptyState>
  );
}
