// Fechas ISO en UTC (las semanas empiezan en lunes).
export const iso = (date) => date.toISOString().slice(0, 10);

export function mondayOf(value) {
  const date = value instanceof Date
    ? new Date(Date.UTC(value.getFullYear(), value.getMonth(), value.getDate()))
    : new Date(`${value}T00:00:00Z`);
  date.setUTCDate(date.getUTCDate() - ((date.getUTCDay() + 6) % 7));
  return iso(date);
}

export function shiftWeek(week, amount) {
  const date = new Date(`${week}T00:00:00Z`);
  date.setUTCDate(date.getUTCDate() + amount * 7);
  return iso(date);
}

export function dayLabel(week, day) {
  const date = new Date(`${week}T00:00:00Z`);
  date.setUTCDate(date.getUTCDate() + day);
  return date.toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit', timeZone: 'UTC' });
}

export const DAY_NAMES = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'];
export const MEALS = ['comida', 'cena'];
