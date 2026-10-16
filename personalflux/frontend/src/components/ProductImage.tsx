import { categoryHue } from "../lib/format";

interface Props {
  title: string;
  category: string | null;
  imageUrl: string | null;
}

/** The dataset has no product photos, so items without one get a stable colour tile. */
export function ProductImage({ title, category, imageUrl }: Props) {
  if (imageUrl) {
    return <img src={imageUrl} alt={title} loading="lazy" className="aspect-square w-full rounded-lg object-cover" />;
  }
  const h = categoryHue(category);
  return (
    <div
      aria-hidden="true"
      className="flex aspect-square w-full items-center justify-center rounded-lg text-xs font-medium text-white/70"
      style={{ background: `linear-gradient(135deg, hsl(${h} 55% 30%), hsl(${(h + 45) % 360} 60% 18%))` }}
    >
      {category ?? "Uncategorised"}
    </div>
  );
}
