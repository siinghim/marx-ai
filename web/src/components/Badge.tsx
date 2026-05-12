export default function Badge() {
  return (
    <div className="flex items-center gap-2 px-3 py-3 border-b border-gray-700">
      <div className="w-8 h-8 bg-red-600 rounded-full flex items-center justify-center text-yellow-400 text-lg font-bold">
        ★
      </div>
      <span className="text-white font-semibold text-sm">Marx AI</span>
    </div>
  );
}
