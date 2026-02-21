import SwiftUI

struct RootTabView: View {
    @EnvironmentObject private var container: AppContainer

    var body: some View {
        TabView {
            ScannerView(
                viewModel: ScannerViewModel(
                    openFoodFactsService: container.openFoodFactsService,
                    scoringService: container.scoringService,
                    disposalService: container.disposalService,
                    scanStore: container.scanStore
                )
            )
            .tabItem { Label("Scan", systemImage: "barcode.viewfinder") }

            HistoryView(viewModel: HistoryViewModel(scanStore: container.scanStore))
                .tabItem { Label("History", systemImage: "clock.arrow.circlepath") }

            AnalyticsView(
                viewModel: AnalyticsViewModel(
                    scanStore: container.scanStore,
                    reportService: container.reportService
                )
            )
            .tabItem { Label("Impact", systemImage: "chart.bar.xaxis") }
        }
        .tint(EcoTheme.accent)
    }
}
