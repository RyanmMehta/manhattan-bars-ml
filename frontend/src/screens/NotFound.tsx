import { Link } from 'react-router-dom';
import { EmptyState } from '../components/ui/EmptyState';

export function NotFound() {
  return (
    <EmptyState
      title="Nothing here"
      body="That page doesn’t exist."
      action={
        <Link to="/tonight" className="text-accent underline">
          Go to tonight’s pick
        </Link>
      }
    />
  );
}
