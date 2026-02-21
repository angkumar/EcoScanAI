import SwiftUI

struct HistoryView: View {
    @StateObject var viewModel: HistoryViewModel

    var body: some View {
        ZStack {
            AnimatedBackgroundView().ignoresSafeArea()

            VStack(spacing: 12) {
                summary
                list
            }
            .padding(16)
            .onAppear { viewModel.refresh() }
        }
    }

    private var summary: some View {
        HStack(spacing: 10) {
            summaryCard(title: "Weekly Scans", value: "\(viewModel.weeklySummary.totalScans)")
            summaryCard(title: "Weekly CO2", value: "\(viewModel.weeklySummary.totalCO2, specifier: "%.1f") kg")
            summaryCard(title: "Streak", value: "\(viewModel.weeklySummary.streakDays) 🔥")
        }
    }

    private func summaryCard(title: String, value: String) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(value)
                .font(.system(.headline, design: .rounded, weight: .bold))
                .foregroundStyle(.white)
            Text(title)
                .font(.system(.caption, design: .rounded))
                .foregroundStyle(.white.opacity(0.7))
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .glowCard()
    }

    private var list: some View {
        List(viewModel.scans) { scan in
            HStack(spacing: 10) {
                VStack(alignment: .leading, spacing: 3) {
                    Text(scan.productName)
                        .foregroundStyle(.white)
                    Text(scan.timestamp.formatted(date: .abbreviated, time: .shortened))
                        .foregroundStyle(.white.opacity(0.65))
                        .font(.caption)
                }

                Spacer()

                VStack(alignment: .trailing, spacing: 3) {
                    Text(scan.impactScore.rawValue)
                        .foregroundStyle(scan.impactScore.color)
                    Text("\(scan.co2Estimate, specifier: "%.1f") kg")
                        .foregroundStyle(.white.opacity(0.75))
                        .font(.caption)
                }
            }
            .listRowBackground(Color.white.opacity(0.05))
        }
        .scrollContentBackground(.hidden)
        .listStyle(.plain)
        .clipShape(RoundedRectangle(cornerRadius: 18))
    }
}
