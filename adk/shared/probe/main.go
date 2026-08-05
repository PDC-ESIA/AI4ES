// probe é um cliente HTTP estático, injetado via `docker cp` e executado via
// `docker exec` — bate nas rotas de dentro do próprio container, sem depender
// de curl/wget/python estarem instalados na imagem.
//
// Uso: probe <caminho-para-request-spec.json> [base_url]
package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"time"
)

type Requisicao struct {
	Metodo    string            `json:"method"`
	Path      string            `json:"path"`
	Headers   map[string]string `json:"headers,omitempty"`
	Body      string            `json:"body,omitempty"`
	TimeoutMs int               `json:"timeout_ms"`
}

type Resultado struct {
	Metodo     string  `json:"method"`
	Path       string  `json:"path"`
	Status     int     `json:"status"`
	LatenciaMs int64   `json:"latency_ms"`
	Erro       *string `json:"error"`
	Body       string  `json:"body,omitempty"`
}

func executar(base string, r Requisicao) Resultado {
	timeout := time.Duration(r.TimeoutMs) * time.Millisecond
	if timeout <= 0 {
		timeout = 5 * time.Second
	}
	cliente := &http.Client{Timeout: timeout}

	var corpo io.Reader
	if r.Body != "" {
		corpo = bytes.NewBufferString(r.Body)
	}

	req, err := http.NewRequest(r.Metodo, base+r.Path, corpo)
	if err != nil {
		msg := fmt.Sprintf("requisicao_invalida: %v", err)
		return Resultado{Metodo: r.Metodo, Path: r.Path, Status: 0, Erro: &msg}
	}
	for k, v := range r.Headers {
		req.Header.Set(k, v)
	}
	if r.Body != "" && req.Header.Get("Content-Type") == "" {
		req.Header.Set("Content-Type", "application/json")
	}

	t0 := time.Now()
	resp, err := cliente.Do(req)
	latencia := time.Since(t0).Milliseconds()

	if err != nil {
		// Falha de TRANSPORTE — a única coisa que este probe trata como erro.
		// Qualquer resposta HTTP recebida, mesmo 4xx/5xx, NÃO é erro aqui.
		msg := classificarErro(err)
		return Resultado{Metodo: r.Metodo, Path: r.Path, Status: 0, LatenciaMs: latencia, Erro: &msg}
	}
	defer resp.Body.Close()

	corpoResp, _ := io.ReadAll(io.LimitReader(resp.Body, 64*1024))
	return Resultado{
		Metodo: r.Metodo, Path: r.Path, Status: resp.StatusCode,
		LatenciaMs: latencia, Erro: nil, Body: string(corpoResp),
	}
}

func classificarErro(err error) string {
	if os.IsTimeout(err) {
		return "timeout"
	}
	return "connection_error: " + err.Error()
}

func main() {
	if len(os.Args) < 2 {
		fmt.Fprintln(os.Stderr, "uso: probe <request-spec.json> [base_url]")
		os.Exit(2)
	}
	baseURL := "http://localhost"
	if len(os.Args) >= 3 {
		baseURL = os.Args[2]
	}

	dados, err := os.ReadFile(os.Args[1])
	if err != nil {
		fmt.Fprintf(os.Stderr, "erro ao ler request-spec: %v\n", err)
		os.Exit(2)
	}

	var requisicoes []Requisicao
	if err := json.Unmarshal(dados, &requisicoes); err != nil {
		fmt.Fprintf(os.Stderr, "request-spec.json invalido: %v\n", err)
		os.Exit(2)
	}

	resultados := make([]Resultado, 0, len(requisicoes))
	for _, r := range requisicoes {
		resultados = append(resultados, executar(baseURL, r))
	}

	saida, _ := json.Marshal(resultados)
	fmt.Println(string(saida))
}
