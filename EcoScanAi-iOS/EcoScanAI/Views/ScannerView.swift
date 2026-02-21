import SwiftUI

struct ScannerView: View {
    @StateObject var viewModel: ScannerViewModel
    @State private var showBadge = false

    var body: some View {
        ZStack {
            AnimatedBackgroundView()
                .ignoresSafeArea()

            ScrollView(showsIndicators: false) {
                VStack(spacing: 14) {
                    header
                    scannerCard
                    controls
                    resultCard
                }
                .padding(.horizontal, 16)
                .padding(.vertical, 12)
            }
        }
        .onAppear {
            viewModel.requestCameraPermission()
        }
        .alert("Scan Error", isPresented: Binding(get: {
            viewModel.errorMessage != nil
        }, set: { _ in
            viewModel.errorMessage = nil
        })) {
            Button("OK", role: .cancel) {}
        } message: {
            Text(viewModel.errorMessage ?? "")
        }
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("EcoScan AI")
                .font(.system(size: 34, weight: .black, design: .rounded))
                .foregroundStyle(.white)
            Text("Scan. Understand. Reduce.")
                .font(.system(size: 15, weight: .semibold, design: .rounded))
                .foregroundStyle(.white.opacity(0.75))
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .glowCard()
    }

    private var scannerCard: some View {
        ZStack(alignment: .bottom) {
            BarcodeScannerView(isScanning: viewModel.isScanning) { code in
                viewModel.onDetectedBarcode(code)
            }
            .frame(height: 280)
            .clipShape(RoundedRectangle(cornerRadius: 22))

            Text(viewModel.isScanning ? "Scanning..." : "Camera idle")
                .font(.system(.footnote, design: .rounded, weight: .bold))
                .foregroundStyle(.white)
                .padding(.horizontal, 14)
                .padding(.vertical, 8)
                .background(.black.opacity(0.5), in: Capsule())
                .padding(12)
        }
        .overlay(RoundedRectangle(cornerRadius: 22).stroke(EcoTheme.stroke, lineWidth: 1))
        .shadow(color: EcoTheme.accent.opacity(0.20), radius: 14, x: 0, y: 8)
    }

    private var controls: some View {
        VStack(spacing: 12) {
            Picker("City", selection: $viewModel.selectedCity) {
                ForEach(City.allCases) { city in
                    Text(city.rawValue).tag(city)
                }
            }
            .pickerStyle(.segmented)

            TextField("Manual barcode fallback", text: $viewModel.manualBarcode)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled(true)
                .keyboardType(.numbersAndPunctuation)
                .padding(12)
                .background(Color.white.opacity(0.08), in: RoundedRectangle(cornerRadius: 14))
                .foregroundStyle(.white)

            HStack(spacing: 10) {
                Button(viewModel.isScanning ? "Stop Camera" : "Start Camera") {
                    withAnimation(.spring(response: 0.35, dampingFraction: 0.8)) {
                        viewModel.isScanning.toggle()
                    }
                }
                .buttonStyle(AccentButtonStyle())

                Button("Analyze") {
                    viewModel.analyzeBarcode()
                }
                .buttonStyle(AccentButtonStyle())
                .disabled(viewModel.isLoading)
            }

            if let analysis = viewModel.latestAnalysis {
                ShareLink(item: analysis.shareSummary) {
                    Label("Share", systemImage: "square.and.arrow.up")
                        .font(.system(.subheadline, design: .rounded, weight: .bold))
                        .foregroundStyle(.white)
                }
            }
        }
        .glowCard()
    }

    @ViewBuilder
    private var resultCard: some View {
        if let analysis = viewModel.latestAnalysis {
            VStack(alignment: .leading, spacing: 12) {
                HStack(alignment: .top, spacing: 12) {
                    AsyncImage(url: analysis.product.imageURL) { image in
                        image
                            .resizable()
                            .scaledToFill()
                    } placeholder: {
                        RoundedRectangle(cornerRadius: 14)
                            .fill(Color.white.opacity(0.10))
                    }
                    .frame(width: 92, height: 92)
                    .clipShape(RoundedRectangle(cornerRadius: 14))

                    VStack(alignment: .leading, spacing: 4) {
                        Text(analysis.product.name)
                            .foregroundStyle(.white)
                            .font(.system(.title3, design: .rounded, weight: .bold))
                        Text(analysis.product.category)
                            .foregroundStyle(.white.opacity(0.7))
                            .font(.system(.footnote, design: .rounded))
                    }
                    Spacer()
                }

                ImpactBadgeView(score: analysis.impactScore)
                    .scaleEffect(showBadge ? 1.0 : 0.7)
                    .opacity(showBadge ? 1 : 0)
                    .onAppear {
                        withAnimation(.spring(response: 0.45, dampingFraction: 0.75)) {
                            showBadge = true
                        }
                    }

                Text(analysis.reason)
                    .foregroundStyle(.white.opacity(0.78))
                    .font(.system(.subheadline, design: .rounded))

                DisposalCardView(instruction: analysis.disposalInstruction)

                VStack(alignment: .leading, spacing: 6) {
                    Text("Lower-impact alternative")
                        .font(.system(.caption, design: .rounded, weight: .bold))
                        .foregroundStyle(EcoTheme.accent)
                    Text(analysis.suggestedAlternative)
                        .foregroundStyle(.white)
                }

                HStack {
                    Text("CO2 estimate")
                        .foregroundStyle(.white.opacity(0.75))
                    Spacer()
                    Text("\(analysis.impactScore.co2Estimate, specifier: "%.1f") kg")
                        .foregroundStyle(.white)
                        .font(.system(.headline, design: .rounded, weight: .bold))
                }

                Button("Save to History") {
                    viewModel.saveCurrentScan()
                }
                .buttonStyle(AccentButtonStyle())
            }
            .glowCard()
            .transition(.asymmetric(insertion: .move(edge: .bottom).combined(with: .opacity), removal: .opacity))
        }
    }
}

private struct AccentButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .frame(maxWidth: .infinity)
            .padding(.vertical, 12)
            .font(.system(.headline, design: .rounded, weight: .bold))
            .foregroundStyle(.black)
            .background(EcoTheme.accent.opacity(configuration.isPressed ? 0.72 : 1.0), in: RoundedRectangle(cornerRadius: 14))
    }
}
