import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import type { ChartConfig } from '../types';

interface ResultsChartProps {
  data: Record<string, unknown>[];
  config: ChartConfig;
}

const COLORS = ['#58a6ff', '#bc8cff', '#3fb950', '#f85149', '#d29922', '#79c0ff', '#a371f7'];

export function ResultsChart({ data, config }: ResultsChartProps) {
  const { chart_type, x_axis, y_axis, title } = config;

  if (!data || data.length === 0) {
    return null;
  }

  // Handle wide-format (single row with multiple metrics)
  let chartData = data;
  let xKey = x_axis;
  let yKey = y_axis;

  if (x_axis === '__columns__' && y_axis === '__values__' && data.length === 1) {
    const numericCols = Object.keys(data[0]).filter(
      (k) => typeof data[0][k] === 'number'
    );
    chartData = numericCols.map((col) => ({
      Metric: col,
      Value: data[0][col],
    }));
    xKey = 'Metric';
    yKey = 'Value';
  }

  if (!xKey || !yKey || !chartData[0]?.[xKey]) {
    return null;
  }

  const renderChart = () => {
    switch (chart_type) {
      case 'bar':
        return (
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#30363d" />
            <XAxis dataKey={xKey} stroke="#8b949e" />
            <YAxis stroke="#8b949e" />
            <Tooltip
              contentStyle={{ backgroundColor: '#161b22', border: '1px solid #30363d' }}
              labelStyle={{ color: '#e6edf3' }}
            />
            <Legend />
            <Bar dataKey={yKey} fill="#58a6ff" radius={[4, 4, 0, 0]} />
          </BarChart>
        );

      case 'line':
        return (
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#30363d" />
            <XAxis dataKey={xKey} stroke="#8b949e" />
            <YAxis stroke="#8b949e" />
            <Tooltip
              contentStyle={{ backgroundColor: '#161b22', border: '1px solid #30363d' }}
              labelStyle={{ color: '#e6edf3' }}
            />
            <Legend />
            <Line type="monotone" dataKey={yKey} stroke="#bc8cff" strokeWidth={2} dot={{ fill: '#bc8cff' }} />
          </LineChart>
        );

      case 'pie':
        return (
          <PieChart>
            <Pie
              data={chartData}
              dataKey={yKey}
              nameKey={xKey}
              cx="50%"
              cy="50%"
              outerRadius={150}
              label
            >
              {chartData.map((_, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{ backgroundColor: '#161b22', border: '1px solid #30363d' }}
              labelStyle={{ color: '#e6edf3' }}
            />
            <Legend />
          </PieChart>
        );

      case 'scatter':
        return (
          <ScatterChart>
            <CartesianGrid strokeDasharray="3 3" stroke="#30363d" />
            <XAxis dataKey={xKey} stroke="#8b949e" type="number" />
            <YAxis dataKey={yKey} stroke="#8b949e" type="number" />
            <Tooltip
              contentStyle={{ backgroundColor: '#161b22', border: '1px solid #30363d' }}
              labelStyle={{ color: '#e6edf3' }}
            />
            <Legend />
            <Scatter name={title} data={chartData} fill="#3fb950" />
          </ScatterChart>
        );

      default:
        return null;
    }
  };

  return (
    <div className="chart-container">
      <ResponsiveContainer width="100%" height={350}>
        {renderChart()}
      </ResponsiveContainer>
    </div>
  );
}
