import { useState } from "react";
import { categoryHue } from "../lib/format";

interface Props {
  title: string;
  category: string | null;
  imageUrl: string | null;
}

function Tile({ category }: { category: string | null }) {
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

/** Real product photos where the catalog has one, otherwise a stable photo per title. */
export function ProductImage({ title, category, imageUrl }: Props) {
  const [failed, setFailed] = useState(false);
  const src = imageUrl && !failed ? imageUrl : `https://picsum.photos/seed/${encodeURIComponent(title)}/600/600`;
  if (!imageUrl && failed) return <Tile category={category} />;
  return (
    <img
      src={src}
      alt={title}
      loading="lazy"
      decoding="async"
      onError={() => setFailed(true)}
      className="aspect-square w-full rounded-lg object-cover"
    />
  );
}
