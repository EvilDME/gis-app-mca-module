import React, { Suspense, lazy, useMemo, useState } from 'react';
import toast from 'react-hot-toast';
import { useMapStore } from '../store/useMapStore';
import McaPanel from './McaPanel';

const RouteStatsPanel = lazy(() => import('./RouteStatsPanel'));

const routeModeOptions = [
  {
    id: 'fast',
    label: 'Быстрее',
    field: 55,
    slope: 12,
    tooltipTitle: 'Быстрый режим',
    tooltipText: 'Сильнее тянется к дорогам и меньше боится рельефа. Подходит, когда важнее быстрее добраться до точки.',
  },
  {
    id: 'safe',
    label: 'Безопаснее',
    field: 32,
    slope: 42,
    tooltipTitle: 'Безопасный режим',
    tooltipText: 'Осторожнее относится к рельефу и чаще выбирает более предсказуемые участки движения.',
  },
  {
    id: 'scenic',
    label: 'Живописнее',
    field: 22,
    slope: 28,
    tooltipTitle: 'Живописный режим',
    tooltipText: 'Чуть охотнее уходит с магистральных дорог и старается держать маршрут визуально приятным и спокойным.',
  },
];

const mobileTabs = [
  { id: 'route', label: 'Маршрут' },
  { id: 'analysis', label: 'Анализ' },
  { id: 'reviews', label: 'Отзывы' },
];

export default function Sidebar({ isOpen, onClose }) {
  const store = useMapStore();
  const [openSection, setOpenSection] = useState('routing');
  const [activeTooltip, setActiveTooltip] = useState(null);
  const [mobileTab, setMobileTab] = useState('route');
  const isMobile = typeof window !== 'undefined' && window.innerWidth < 768;

  const activeRouteMode = routeModeOptions.find((option) => option.id === store.routeMode) || routeModeOptions[1];
  const myReviews = useMemo(
    () => (store.user ? store.reviews.filter((review) => review.user_id === store.user.id) : []),
    [store.reviews, store.user]
  );

  const closeForMapAction = () => {
    if (isMobile) {
      onClose?.();
    }
  };

  const toggleTooltip = (name) => {
    setActiveTooltip(activeTooltip === name ? null : name);
  };

  const exportGPX = () => {
    if (!store.routePath) return;

    const trkpts = store.routePath
      .map((point, index) => {
        const ele = store.routeStats?.profile?.[index] || 0;
        return `      <trkpt lat="${point[0]}" lon="${point[1]}"><ele>${ele}</ele></trkpt>`;
      })
      .join('\n');

    const gpxData = `<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="EcoMapApp">
  <trk>
    <name>Мой Эко-Маршрут</name>
    <trkseg>\n${trkpts}\n    </trkseg>
  </trk>
</gpx>`;

    const blob = new Blob([gpxData], { type: 'application/gpx+xml' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'eco_route.gpx';
    link.click();
    URL.revokeObjectURL(url);
    toast.success('Маршрут сохранен в формате GPX!');
  };

  const renderModeButtons = () => (
    <div className="space-y-2">
      <p className="text-xs font-bold text-gray-700">Режим маршрута</p>
      <div className="grid grid-cols-3 gap-2">
        {routeModeOptions.map((option) => (
          <div key={option.id} className="relative">
            <button
              type="button"
              onClick={() => !store.exactRouting && store.setRouteMode(option.id)}
              disabled={store.exactRouting}
              className={`w-full rounded-xl border px-2 py-2 text-xs font-semibold transition ${
                store.routeMode === option.id
                  ? 'border-blue-600 bg-blue-600 text-white'
                  : 'border-gray-300 bg-white text-gray-700 hover:bg-gray-50'
              } ${store.exactRouting ? 'cursor-not-allowed opacity-50' : ''}`}
            >
              {option.label}
            </button>
            <button
              type="button"
              onClick={() => toggleTooltip(`mode-${option.id}`)}
              className="absolute right-1 top-1 flex h-5 w-5 items-center justify-center rounded-full bg-white/90 text-[10px] font-bold text-gray-600 shadow"
            >
              ?
            </button>
          </div>
        ))}
      </div>

      {routeModeOptions.map((option) =>
        activeTooltip === `mode-${option.id}` ? (
          <div key={`tooltip-${option.id}`} className="rounded-xl bg-gray-800 p-3 text-xs text-white shadow-md">
            <div className="mb-1 font-bold">{option.tooltipTitle}</div>
            <div>{option.tooltipText}</div>
            <div className="mt-2 text-gray-300">
              Лес/поле: {option.field}% | Уклон: {option.slope}%
            </div>
          </div>
        ) : null
      )}

      <div className="rounded-xl border border-blue-100 bg-blue-50 px-3 py-3 text-xs text-slate-700">
        <div><b>Текущий пресет:</b> {activeRouteMode.label}</div>
        <div className="mt-1">
          Лес/поле: <b>{activeRouteMode.field}%</b> | Уклон: <b>{activeRouteMode.slope}%</b>
        </div>
        {store.exactRouting && (
          <div className="mt-1 text-amber-700">
            При включенной точной настройке режимы заблокированы, а значения задаются ползунками ниже.
          </div>
        )}
      </div>
    </div>
  );

  const renderExactSettings = () =>
    store.exactRouting ? (
      <div className="space-y-4 rounded-2xl border border-gray-200 bg-white p-4">
        <div className="relative">
          <div className="mb-1 flex items-center justify-between">
            <label className="flex items-center text-xs font-bold text-gray-700">
              Сложность леса/поля
              <button
                type="button"
                onClick={() => toggleTooltip('field')}
                className="ml-2 flex h-4 w-4 items-center justify-center rounded-full bg-gray-200 text-[10px] text-gray-600"
              >
                ?
              </button>
            </label>
            <span className="text-xs text-gray-500">{store.routeWeights.field}%</span>
          </div>

          {activeTooltip === 'field' && (
            <div className="mb-3 rounded-xl bg-gray-800 p-3 text-xs text-white shadow-md">
              <p className="mb-1"><b>Определяет маршрут по типу местности:</b></p>
              <ul className="list-disc space-y-1 pl-4">
                <li><b>100%</b> — маршрут только по безопасным дорогам.</li>
                <li><b>0%</b> — готовность идти напролом по пересеченной местности.</li>
              </ul>
            </div>
          )}

          <input
            type="range"
            min="0"
            max="100"
            step="5"
            value={store.routeWeights.field}
            onChange={(e) => store.setRouteWeights({ ...store.routeWeights, field: Number(e.target.value) })}
            className="mt-1 w-full"
          />
        </div>

        <div className="relative">
          <div className="mb-1 flex items-center justify-between">
            <label className="flex items-center text-xs font-bold text-gray-700">
              Штраф за уклон
              <button
                type="button"
                onClick={() => toggleTooltip('slope')}
                className="ml-2 flex h-4 w-4 items-center justify-center rounded-full bg-gray-200 text-[10px] text-gray-600"
              >
                ?
              </button>
            </label>
            <span className="text-xs text-gray-500">{store.routeWeights.slope}%</span>
          </div>

          {activeTooltip === 'slope' && (
            <div className="mb-3 rounded-xl bg-gray-800 p-3 text-xs text-white shadow-md">
              <p className="mb-1"><b>Готовность к физическим нагрузкам на рельефе:</b></p>
              <ul className="list-disc space-y-1 pl-4">
                <li><b>100%</b> — пологий маршрут в обход холмов.</li>
                <li><b>0%</b> — более прямой путь через рельеф.</li>
              </ul>
            </div>
          )}

          <input
            type="range"
            min="0"
            max="100"
            step="5"
            value={store.routeWeights.slope}
            onChange={(e) => store.setRouteWeights({ ...store.routeWeights, slope: Number(e.target.value) })}
            className="mt-1 w-full"
          />
        </div>
      </div>
    ) : null;

  const renderRouteActions = () => (
    <div className="space-y-3 rounded-2xl border border-blue-100 bg-blue-50 p-4">
      <div className="text-xs font-bold uppercase tracking-wide text-blue-700">Быстрые действия</div>
      <button
        onClick={() => {
          store.setClickMode(store.clickMode === 'routeA' ? null : 'routeA');
          closeForMapAction();
        }}
        className={`w-full rounded-xl border py-3 text-sm font-semibold transition ${
          store.clickMode === 'routeA' ? 'border-blue-600 bg-blue-600 text-white' : 'bg-white hover:bg-gray-50'
        }`}
      >
        Точка Старта: {store.routeStart ? 'Задана' : 'Выбрать'}
      </button>
      <button
        onClick={() => {
          store.setClickMode(store.clickMode === 'routeB' ? null : 'routeB');
          closeForMapAction();
        }}
        className={`w-full rounded-xl border py-3 text-sm font-semibold transition ${
          store.clickMode === 'routeB' ? 'border-blue-600 bg-blue-600 text-white' : 'bg-white hover:bg-gray-50'
        }`}
      >
        Точка Финиша: {store.routeEnd ? 'Задана' : 'Выбрать'}
      </button>

      {store.routeProgress > 0 ? (
        <div className="relative h-10 w-full overflow-hidden rounded-xl bg-gray-200">
          <div
            className="flex h-10 items-center justify-center bg-blue-600 transition-all duration-200"
            style={{ width: `${store.routeProgress}%` }}
          >
            <span className="absolute w-full text-center text-xs font-bold text-white">
              {store.routeProgress === 100 ? 'Готово' : `Анализ: ${store.routeProgress}%`}
            </span>
          </div>
        </div>
      ) : (
        <button
          onClick={store.calculateRoute}
          disabled={!store.routeStart || !store.routeEnd}
          className={`w-full rounded-xl py-3 text-sm font-bold text-white transition ${
            store.routeStart && store.routeEnd ? 'bg-blue-600 hover:bg-blue-700 shadow-md' : 'bg-gray-300 cursor-not-allowed'
          }`}
        >
          Рассчитать путь
        </button>
      )}

      <button
        onClick={() => {
          store.clearRoute();
          closeForMapAction();
        }}
        className="w-full rounded-xl border border-red-100 bg-white py-3 text-sm font-semibold text-red-600 transition hover:bg-red-50"
      >
        Очистить маршрут
      </button>
    </div>
  );

  const renderRouteSettingsCard = () => (
    <div className="space-y-4 rounded-2xl border border-gray-200 bg-white p-4">
      {renderModeButtons()}

      <label className="flex items-center justify-between rounded-xl border border-gray-200 bg-gray-50 px-3 py-3">
        <span className="text-sm font-medium text-gray-700">Точная настройка</span>
        <input
          type="checkbox"
          checked={store.exactRouting}
          onChange={(e) => store.setExactRouting(e.target.checked)}
          className="h-4 w-4"
        />
      </label>

      {renderExactSettings()}
    </div>
  );

  const renderRouteStats = () =>
    store.routeStats ? (
      <div className="rounded-2xl border border-gray-200 bg-white p-4">
        <Suspense fallback={<div className="text-sm text-gray-500">Загрузка статистики...</div>}>
          <RouteStatsPanel stats={store.routeStats} compact={isMobile} />
        </Suspense>
      </div>
    ) : null;

  const renderGpxCard = () =>
    store.routePath ? (
      <button
        onClick={exportGPX}
        className="w-full rounded-2xl bg-green-600 py-3 font-bold text-white shadow transition hover:bg-green-700"
      >
        Скачать GPX трек
      </button>
    ) : null;

  const renderAnalysisContent = () => (
    <div className="space-y-4">
      <div className="rounded-2xl border border-gray-200 bg-white p-4">
        <div className="mb-3 text-sm font-bold text-slate-800">Буферная зона</div>
        <button
          onClick={() => {
            store.setClickMode(store.clickMode === 'buffer' ? null : 'buffer');
            closeForMapAction();
          }}
          className={`w-full rounded-xl border px-3 py-3 text-left text-sm transition ${
            store.clickMode === 'buffer'
              ? 'border-blue-500 bg-blue-50 text-blue-800'
              : 'border-gray-300 bg-white hover:bg-gray-50'
          }`}
        >
          Центр буфера
        </button>

        <div className="mt-4 rounded-xl border border-gray-200 bg-gray-50 p-3">
          <label className="mb-1 block text-xs font-bold text-gray-700">Радиус буфера (метры)</label>
          <input
            type="number"
            value={store.bufferRadius}
            onChange={(e) => store.setBufferRadius(Number(e.target.value))}
            className="mb-3 w-full rounded-lg border border-gray-300 p-2 text-sm outline-none"
          />
          <button
            onClick={() => store.setShowBuffer(!store.showBuffer)}
            className={`w-full rounded-xl py-3 text-sm font-medium text-white transition ${
              store.showBuffer ? 'bg-red-600 hover:bg-red-700' : 'bg-blue-600 hover:bg-blue-700'
            }`}
          >
            {store.showBuffer ? 'Скрыть буфер' : 'Построить буфер'}
          </button>
        </div>
      </div>
    </div>
  );

  const renderReviewsContent = () => (
    <div className="space-y-4">
      <div className="rounded-2xl border border-gray-200 bg-white p-4">
        <div className="mb-3 text-sm font-bold text-slate-800">Мои отзывы</div>
        {!store.user ? (
          <div className="rounded-xl border border-dashed border-gray-200 bg-gray-50 px-3 py-4 text-sm text-gray-500">
            Войдите в аккаунт, чтобы видеть свои отзывы.
          </div>
        ) : myReviews.length === 0 ? (
          <div className="rounded-xl border border-dashed border-gray-200 bg-gray-50 px-3 py-4 text-sm text-gray-500">
            У вас пока нет отзывов на карте.
          </div>
        ) : (
          <div className="space-y-2">
            {myReviews.map((review) => (
              <button
                key={review.id}
                type="button"
                onClick={() => {
                  store.setSelectedReview(review);
                  closeForMapAction();
                }}
                className="w-full rounded-xl border border-slate-200 bg-white px-3 py-3 text-left transition hover:border-blue-300 hover:bg-blue-50"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="truncate text-sm font-semibold text-slate-800">
                      {review.text || 'Отзыв без текста'}
                    </div>
                    <div className="mt-1 text-xs text-slate-500">
                      {Number(review.lat).toFixed(4)}, {Number(review.lng).toFixed(4)}
                    </div>
                  </div>
                  <div className="shrink-0 rounded-full bg-amber-50 px-2 py-1 text-xs font-bold text-amber-700">
                    {review.rating}★
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="rounded-2xl border border-gray-200 bg-white p-4">
        <button
          onClick={() => {
            if (!store.user) {
              toast.error('Для оставления отзыва требуется авторизация!');
              return;
            }
            store.setClickMode(store.clickMode === 'review' ? null : 'review');
            closeForMapAction();
          }}
          className={`w-full rounded-2xl py-3 text-sm font-bold border transition shadow-sm ${
            store.clickMode === 'review'
              ? 'border-green-600 bg-green-600 text-white'
              : 'border-gray-300 bg-white text-gray-800 hover:bg-gray-50'
          }`}
        >
          {store.clickMode === 'review' ? 'Отмена (Режим отзыва)' : 'Оставить отзыв на карте'}
        </button>
      </div>
    </div>
  );

  const renderDesktopAccordionSection = (id, title, content) => (
    <div className="overflow-hidden rounded-lg border border-gray-200">
      <button
        onClick={() => setOpenSection(openSection === id ? null : id)}
        className="w-full bg-gray-100 p-3 text-left font-bold text-gray-800 transition hover:bg-gray-200"
      >
        {title}
      </button>
      {openSection === id && <div className="bg-white p-4">{content}</div>}
    </div>
  );

  const renderMobileLayout = () => (
    <>
      <div className="border-b border-slate-200 bg-white px-4 py-3">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-sky-700">UUST EcoMap</p>
            <h2 className="text-lg font-bold text-slate-900">Инструменты карты</h2>
          </div>
          <button type="button" onClick={onClose} className="rounded-full border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-600">
            Закрыть
          </button>
        </div>
      </div>

      <div className="flex items-center justify-between border-b border-gray-200 bg-gray-50 px-4 py-3">
        {store.user ? (
          <div><p className="text-sm">Пользователь: <span className="font-bold text-gray-800">{store.user.username}</span></p></div>
        ) : (
          <p className="text-sm text-gray-600">Не авторизован</p>
        )}
        <button
          onClick={() => (store.user ? store.logout() : store.setShowAuth(true))}
          className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm transition hover:bg-gray-100"
        >
          {store.user ? 'Выход' : 'Вход'}
        </button>
      </div>

      <div className="grid grid-cols-3 gap-2 border-b border-slate-200 bg-white px-4 py-3">
        {mobileTabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setMobileTab(tab.id)}
            className={`rounded-xl px-3 py-2 text-sm font-semibold transition ${
              mobileTab === tab.id
                ? 'bg-slate-900 text-white'
                : 'border border-slate-200 bg-slate-50 text-slate-600'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div
        className="min-h-0 flex-1 overflow-y-auto bg-slate-100 p-4"
        style={{ WebkitOverflowScrolling: 'touch', touchAction: 'pan-y' }}
      >
        {mobileTab === 'route' && (
          <div className="space-y-4">
            {renderRouteActions()}
            {renderRouteSettingsCard()}
            {renderRouteStats()}
            {renderGpxCard()}
          </div>
        )}

        {mobileTab === 'analysis' && renderAnalysisContent()}
        {mobileTab === 'reviews' && renderReviewsContent()}
      </div>
    </>
  );

  const renderDesktopLayout = () => (
    <>
      <div className="flex items-center justify-between border-b border-gray-200 bg-gray-50 p-4">
        {store.user ? (
          <div><p className="text-sm">Пользователь: <span className="font-bold text-gray-800">{store.user.username}</span></p></div>
        ) : (
          <p className="text-sm text-gray-600">Не авторизован</p>
        )}
        <button
          onClick={() => (store.user ? store.logout() : store.setShowAuth(true))}
          className="rounded border border-gray-300 bg-white px-3 py-1 text-sm transition hover:bg-gray-100"
        >
          {store.user ? 'Выход' : 'Вход'}
        </button>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-4 pb-8 space-y-4">
        <h2 className="mb-2 text-lg font-bold text-gray-800">Инструменты</h2>

        {renderDesktopAccordionSection('routing', 'Построение маршрута', (
          <div className="space-y-4">
            {renderModeButtons()}
            <label className="flex items-center justify-between rounded-xl border border-gray-200 bg-gray-50 px-3 py-3">
              <span className="text-sm font-medium text-gray-700">Точная настройка</span>
              <input
                type="checkbox"
                checked={store.exactRouting}
                onChange={(e) => store.setExactRouting(e.target.checked)}
                className="h-4 w-4"
              />
            </label>
            {renderExactSettings()}
            <hr className="border-gray-200" />
            {renderRouteActions()}
          </div>
        ))}


        {store.routeStats &&
          renderDesktopAccordionSection('stats', 'Статистика маршрута', renderRouteStats())}

        {/* ### КОМПОНЕНТ МИКРОСЕРВИСА ### */}
        {renderDesktopAccordionSection('mca', 'Анализ пригодности территории', <McaPanel />)}
        
        {store.user &&
          renderDesktopAccordionSection('myReviews', 'Мои отзывы', renderReviewsContent())}

        <div className="space-y-3 border-t border-gray-200 pt-4">
          {renderGpxCard()}
          <button
            onClick={() => {
              if (!store.user) {
                toast.error('Для оставления отзыва требуется авторизация!');
                return;
              }
              store.setClickMode(store.clickMode === 'review' ? null : 'review');
            }}
            className={`w-full rounded-2xl py-3 text-sm font-bold border transition shadow-sm ${
              store.clickMode === 'review'
                ? 'border-green-600 bg-green-600 text-white'
                : 'border-gray-300 bg-white text-gray-800 hover:bg-gray-50'
            }`}
          >
            {store.clickMode === 'review' ? 'Отмена (Режим отзыва)' : 'Оставить отзыв на карте'}
          </button>
        </div>
      </div>
    </>
  );

  return (
    <aside
      className={`fixed inset-0 z-[1300] flex h-[100dvh] max-h-[100dvh] flex-col overflow-hidden bg-white transition-transform duration-300 md:static md:h-auto md:max-h-none md:w-[340px] md:border-r md:border-slate-200 md:shadow-lg ${
        isOpen ? 'translate-y-0' : 'translate-y-full md:translate-y-0'
      }`}
    >
      {isMobile ? renderMobileLayout() : renderDesktopLayout()}
    </aside>
  );
}
