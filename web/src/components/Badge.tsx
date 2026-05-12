export default function Badge() {
  return (
    <div className="flex items-center gap-2 px-3 py-3 border-b border-gray-700">
      <img src="/hammer-sickle.svg" alt="Marx AI" className="w-8 h-8" />
      <span className="text-white font-semibold text-sm">Marx AI</span>
    </div>
  );
}
