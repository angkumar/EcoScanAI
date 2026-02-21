import Foundation
import Combine
import AVFoundation

@MainActor
final class ScannerViewModel: ObservableObject {
    @Published var selectedCity: City = .sanFrancisco
    @Published var manualBarcode: String = ""
    @Published var latestAnalysis: ScanAnalysis?
    @Published var isScanning = false
    @Published var isLoading = false
    @Published var errorMessage: String?

    private let openFoodFactsService: OpenFoodFactsService
    private let scoringService: ImpactScoringService
    private let disposalService: DisposalService
    private let scanStore: ScanStore
    private var cancellables = Set<AnyCancellable>()

    init(
        openFoodFactsService: OpenFoodFactsService,
        scoringService: ImpactScoringService,
        disposalService: DisposalService,
        scanStore: ScanStore
    ) {
        self.openFoodFactsService = openFoodFactsService
        self.scoringService = scoringService
        self.disposalService = disposalService
        self.scanStore = scanStore
    }

    func requestCameraPermission() {
        AVCaptureDevice.requestAccess(for: .video) { _ in }
    }

    func onDetectedBarcode(_ code: String) {
        manualBarcode = code
        isScanning = false
        analyzeBarcode()
    }

    func analyzeBarcode() {
        let barcode = manualBarcode.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !barcode.isEmpty else {
            errorMessage = "Enter a barcode or scan with camera."
            return
        }

        isLoading = true
        errorMessage = nil

        openFoodFactsService.fetchProduct(barcode: barcode)
            .sink { [weak self] completion in
                guard let self else { return }
                self.isLoading = false
                if case let .failure(error) = completion {
                    self.errorMessage = error.localizedDescription
                }
            } receiveValue: { [weak self] product in
                guard let self else { return }
                let scoring = self.scoringService.score(product: product)
                let disposal = self.disposalService.instruction(
                    for: self.selectedCity,
                    packagingText: product.packagingText,
                    category: product.category
                )
                let suggestion = self.scoringService.suggestion(for: scoring.score, productName: product.name)

                self.latestAnalysis = ScanAnalysis(
                    product: product,
                    impactScore: scoring.score,
                    reason: scoring.reason,
                    disposalInstruction: disposal,
                    suggestedAlternative: suggestion
                )
            }
            .store(in: &cancellables)
    }

    func saveCurrentScan() {
        guard let analysis = latestAnalysis else { return }

        let record = ScanRecord(
            id: UUID(),
            barcode: analysis.product.barcode,
            productName: analysis.product.name,
            category: analysis.product.category,
            city: selectedCity,
            impactScore: analysis.impactScore,
            co2Estimate: analysis.impactScore.co2Estimate,
            disposalType: analysis.disposalInstruction.disposalType,
            timestamp: Date()
        )

        scanStore.save(record: record)
    }
}
