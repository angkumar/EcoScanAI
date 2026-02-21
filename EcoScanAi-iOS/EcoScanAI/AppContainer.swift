import Foundation

final class AppContainer: ObservableObject {
    let openFoodFactsService: OpenFoodFactsService
    let scoringService: ImpactScoringService
    let disposalService: DisposalService
    let scanStore: ScanStore
    let reportService: PDFReportService

    init() {
        self.openFoodFactsService = OpenFoodFactsService()
        self.scoringService = ImpactScoringService()
        self.disposalService = DisposalService()
        self.scanStore = ScanStore()
        self.reportService = PDFReportService()
    }
}
