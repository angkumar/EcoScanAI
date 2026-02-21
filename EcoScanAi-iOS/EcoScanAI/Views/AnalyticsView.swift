import SwiftUI

struct AnalyticsView: View {
    @StateObject var viewModel: AnalyticsViewModel
    @State private var exportedURL: URL?
    @State private var reportMonth = Date()
    @State private var showingShare = false

    var body: some View {
        ZStack {
            AnimatedBackgroundView().ignoresSafeArea()

            ScrollView(showsIndicators: false) {
                VStack(spacing: 14) {
                    co2Chart
                    impactBreakdown
                    reportExport
                }
                .padding(16)
            }
        }
        .sheet(isPresented: $showingShare) {
            if let exportedURL {
                ActivityView(activityItems: [exportedURL])
            }
        }
    }

    private var co2Chart: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Weekly CO2")
                .font(.system(.headline, design: .rounded, weight: .bold))
                .foregroundStyle(.white)

            HStack(alignment: .bottom, spacing: 10) {
                ForEach(viewModel.weeklyCO2Series) { point in
                    VStack {
                        RoundedRectangle(cornerRadius: 6)
                            .fill(EcoTheme.accent)
                            .frame(width: 26, height: max(8, point.value * 8))
                        Text(point.day)
                            .font(.caption2)
                            .foregroundStyle(.white.opacity(0.7))
                    }
                }
            }
            .frame(maxWidth: .infinity, minHeight: 140, alignment: .bottom)
        }
        .glowCard()
    }

    private var impactBreakdown: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Impact Distribution")
                .font(.system(.headline, design: .rounded, weight: .bold))
                .foregroundStyle(.white)

            ForEach(ImpactScore.allCases, id: \.self) { score in
                HStack {
                    Text(score.rawValue)
                        .foregroundStyle(score.color)
                    Spacer()
                    Text("\(viewModel.impactCounts[score, default: 0])")
                        .foregroundStyle(.white)
                        .font(.system(.body, design: .rounded, weight: .bold))
                }
            }
        }
        .glowCard()
    }

    private var reportExport: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Monthly PDF Report")
                .font(.system(.headline, design: .rounded, weight: .bold))
                .foregroundStyle(.white)

            DatePicker("Month", selection: $reportMonth, displayedComponents: [.date])
                .datePickerStyle(.compact)
                .foregroundStyle(.white)

            Button("Generate & Share Report") {
                do {
                    exportedURL = try viewModel.exportMonthlyReport(for: reportMonth)
                    showingShare = exportedURL != nil
                } catch {
                    exportedURL = nil
                    showingShare = false
                }
            }
            .buttonStyle(PlainButtonStyle())
            .frame(maxWidth: .infinity)
            .padding(.vertical, 12)
            .background(EcoTheme.accent, in: RoundedRectangle(cornerRadius: 14))
            .foregroundStyle(.black)
            .font(.system(.headline, design: .rounded, weight: .bold))
        }
        .glowCard()
    }
}

private struct ActivityView: UIViewControllerRepresentable {
    let activityItems: [Any]

    func makeUIViewController(context: Context) -> UIActivityViewController {
        UIActivityViewController(activityItems: activityItems, applicationActivities: nil)
    }

    func updateUIViewController(_ uiViewController: UIActivityViewController, context: Context) {}
}
